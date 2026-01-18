import { Env } from './utils';

export type SourceConfig = {
    secretKey: keyof Env | string; // Allow string to match generic keys, but ideally keyof Env
    headerNames: string[];
    encoding: 'hex' | 'base64' | 'auto';
};

// Registry of source-specific configurations
export const SOURCE_CONFIGS: Record<string, SourceConfig> = {
    /**
     * Khi Sapo gọi Webhook cho anh:
        * Sapo sẽ lấy nội dung request + Secret Key -> Tạo ra 1 chuỗi ký tự (HMAC).
        * Sapo gửi request + chuỗi HMAC này (qua header X-Sapo-Hmac-Sha256).
        * Server của anh (Cloudflare Worker) cũng lấy nội dung nhận được + SAPO_SECRET (anh cấu hình) -> Tự tính lại HMAC.
        * Nếu 2 chuỗi khớp nhau -> Request chuẩn từ Sapo. Không khớp -> Request giả mạo.
     */
    'sapo': {
        // 'SAPO_SECRET' is the NAME of the environment variable containing the actual secret.
        // You must set SAPO_SECRET in .dev.vars (local) or Cloudflare Dashboard (production).
        secretKey: 'SAPO_SECRET', 
        headerNames: ['x-sapo-hmac-sha256'],
        encoding: 'base64'
    },
    'github': {
        // 'GITHUB_SECRET' is the NAME of the environment variable.
        secretKey: 'GITHUB_SECRET',
        headerNames: ['x-hub-signature-256'],
        encoding: 'hex'
    }
};

// Default fallback configuration (mimics legacy behavior)
export const DEFAULT_CONFIG: SourceConfig = {
     secretKey: 'WEBHOOK_SECRET',
     headerNames: ['x-hub-signature-256'], // Will be overridden by HMAC_HEADER_NAME env var if present in logic
     encoding: 'auto'
};
