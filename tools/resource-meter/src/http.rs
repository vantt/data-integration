//! Minimal HTTP/1.1 POST over `std::net::TcpStream`, for the local Dagster GraphQL
//! endpoint only (plain HTTP on a loopback address; no TLS, no proxies, no redirects).

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::time::Duration;

/// Responses larger than this are rejected (a GraphQL page is about 50 KB).
pub const MAX_RESPONSE_BYTES: usize = 8 * 1024 * 1024;

#[derive(Debug, Clone)]
pub struct Endpoint {
    pub addr: SocketAddr,
    pub path: String,
    pub connect_timeout: Duration,
    pub io_timeout: Duration,
}

impl Endpoint {
    /// Parses `HOST:PORT[/path]` where HOST is a loopback IP address.
    pub fn parse_loopback(spec: &str) -> Result<Self, String> {
        let (hostport, path) = match spec.find('/') {
            Some(i) => (&spec[..i], spec[i..].to_string()),
            None => (spec, "/graphql".to_string()),
        };
        let addr: SocketAddr = hostport
            .parse()
            .map_err(|_| format!("{spec}: expected IP:PORT[/path], e.g. 127.0.0.1:3000"))?;
        if !addr.ip().is_loopback() {
            return Err(format!("{spec}: only a loopback address is allowed"));
        }
        if path.bytes().any(|b| b.is_ascii_whitespace() || b.is_ascii_control()) {
            return Err(format!("{spec}: invalid path"));
        }
        Ok(Self {
            addr,
            path,
            connect_timeout: Duration::from_secs(2),
            io_timeout: Duration::from_secs(10),
        })
    }

    /// POSTs a JSON body and returns the response body of a 200 response.
    pub fn post_json(&self, body: &[u8]) -> Result<Vec<u8>, String> {
        let mut stream = TcpStream::connect_timeout(&self.addr, self.connect_timeout)
            .map_err(|e| format!("connect {}: {e}", self.addr))?;
        stream
            .set_read_timeout(Some(self.io_timeout))
            .map_err(|e| e.to_string())?;
        stream
            .set_write_timeout(Some(self.io_timeout))
            .map_err(|e| e.to_string())?;
        let head = format!(
            "POST {} HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nAccept: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            self.path,
            self.addr,
            body.len()
        );
        stream.write_all(head.as_bytes()).map_err(|e| format!("send: {e}"))?;
        stream.write_all(body).map_err(|e| format!("send: {e}"))?;

        let mut raw = Vec::new();
        stream
            .take(MAX_RESPONSE_BYTES as u64 + 64 * 1024)
            .read_to_end(&mut raw)
            .map_err(|e| format!("receive: {e}"))?;
        parse_response(&raw)
    }
}

fn find(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).position(|w| w == needle)
}

/// Splits status, headers and body; decodes `Transfer-Encoding: chunked`.
pub fn parse_response(raw: &[u8]) -> Result<Vec<u8>, String> {
    let head_end = find(raw, b"\r\n\r\n").ok_or("incomplete HTTP response")?;
    let head = std::str::from_utf8(&raw[..head_end]).map_err(|_| "non-UTF-8 HTTP header")?;
    let mut lines = head.split("\r\n");
    let status_line = lines.next().unwrap_or("");
    let code = status_line.split_ascii_whitespace().nth(1).unwrap_or("");
    if code != "200" {
        return Err(format!("HTTP status {}", if code.is_empty() { "?" } else { code }));
    }
    let mut chunked = false;
    let mut length: Option<usize> = None;
    for line in lines {
        let Some((name, value)) = line.split_once(':') else {
            continue;
        };
        let value = value.trim();
        if name.eq_ignore_ascii_case("transfer-encoding") && value.eq_ignore_ascii_case("chunked") {
            chunked = true;
        } else if name.eq_ignore_ascii_case("content-length") {
            length = Some(value.parse().map_err(|_| "bad Content-Length")?);
        }
    }
    let body = &raw[head_end + 4..];
    let out = if chunked {
        decode_chunked(body)?
    } else if let Some(n) = length {
        body.get(..n).ok_or("truncated HTTP body")?.to_vec()
    } else {
        body.to_vec()
    };
    if out.len() > MAX_RESPONSE_BYTES {
        return Err("HTTP response too large".into());
    }
    Ok(out)
}

fn decode_chunked(mut body: &[u8]) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    loop {
        let line_end = find(body, b"\r\n").ok_or("truncated chunk header")?;
        let size_text = std::str::from_utf8(&body[..line_end]).map_err(|_| "bad chunk header")?;
        let size_hex = size_text.split(';').next().unwrap_or("").trim();
        let size = usize::from_str_radix(size_hex, 16).map_err(|_| "bad chunk size")?;
        body = &body[line_end + 2..];
        if size == 0 {
            return Ok(out);
        }
        if out.len() + size > MAX_RESPONSE_BYTES {
            return Err("HTTP response too large".into());
        }
        let chunk = body.get(..size).ok_or("truncated chunk")?;
        out.extend_from_slice(chunk);
        body = body.get(size + 2..).ok_or("truncated chunk")?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::TcpListener;
    use std::thread;

    #[test]
    fn endpoint_must_be_loopback() {
        let e = Endpoint::parse_loopback("127.0.0.1:3000").unwrap();
        assert_eq!(e.path, "/graphql");
        assert_eq!(Endpoint::parse_loopback("[::1]:13000/gql").unwrap().path, "/gql");
        assert!(Endpoint::parse_loopback("10.0.0.5:3000").is_err());
        assert!(Endpoint::parse_loopback("localhost:3000").is_err());
        assert!(Endpoint::parse_loopback("127.0.0.1").is_err());
    }

    #[test]
    fn parses_length_and_chunked_bodies() {
        let r = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nX: y\r\n\r\nhelloEXTRA";
        assert_eq!(parse_response(r).unwrap(), b"hello");
        let c = b"HTTP/1.1 200 OK\r\ntransfer-encoding: chunked\r\n\r\n3\r\nabc\r\n4;ext=1\r\ndefg\r\n0\r\n\r\n";
        assert_eq!(parse_response(c).unwrap(), b"abcdefg");
        assert!(parse_response(b"HTTP/1.1 500 Internal\r\n\r\n")
            .unwrap_err()
            .contains("500"));
        assert!(parse_response(b"HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\nshort").is_err());
        assert!(parse_response(b"garbage").is_err());
        assert!(parse_response(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\n").is_err());
    }

    #[test]
    fn posts_to_local_server() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let server = thread::spawn(move || {
            let (mut s, _) = listener.accept().unwrap();
            let mut buf = vec![0u8; 4096];
            let mut got = Vec::new();
            while find(&got, b"{\"q\":1}").is_none() {
                let n = s.read(&mut buf).unwrap();
                if n == 0 {
                    break;
                }
                got.extend_from_slice(&buf[..n]);
            }
            s.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}")
                .unwrap();
            String::from_utf8(got).unwrap()
        });
        let e = Endpoint::parse_loopback(&format!("{addr}")).unwrap();
        assert_eq!(e.post_json(b"{\"q\":1}").unwrap(), b"{}");
        let request = server.join().unwrap();
        assert!(request.starts_with("POST /graphql HTTP/1.1\r\n"));
        assert!(request.contains("Content-Length: 7\r\n"));
    }

    #[test]
    fn connection_refused_is_an_error() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        drop(listener);
        assert!(Endpoint::parse_loopback(&addr.to_string())
            .unwrap()
            .post_json(b"{}")
            .is_err());
    }
}
