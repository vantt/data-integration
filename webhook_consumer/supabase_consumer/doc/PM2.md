# Using PM2 to start application automatically

`pm2` is a popular process manager for Node.js applications that can also be configured to start your app on system boot.

1. **Install `pm2`**
   If you haven’t installed `pm2`, you can do so globally using npm:

   ```bash
   npm install -g pm2
   pm2 install pm2-logrotate
   ```

2. **Configure Log Rotation Settings**

After installing, you can configure the log rotation settings according to your needs. For example, you might want to set the maximum log size and retention policy:

```bash
pm2 set pm2-logrotate:max_size 10M  # Rotate logs when they reach 10 MB
pm2 set pm2-logrotate:retain 10      # Keep the last 30 rotated logs
pm2 set pm2-logrotate:compress true   # Enable compression for rotated logs
```

3. **Modify Your PM2 Start Command**

You can start your application without specifying a log file path since `pm2-logrotate` will handle log management automatically. Here’s how your command would look:

```bash
pm2 start dist/consumer.js --name "webhook-consumer" --interpreter node
pm2 start node --name "my-consumer" -- --loader ts-node/esm src/consumer.ts
```

4. **Set Up Autostart**

To ensure that `pm2` restarts your application on system boot, use the following command:

```bash
pm2 startup
```

This command will generate a command specific to your system that you need to run in the terminal.

5. **Save the Current Process List**:
   Finally, save your current process list so that it can be restored on reboot:

   ```bash
   pm2 save
   ```

6. **Test It**:

   Restart your Mac and verify that your application is running by checking with:

   ```bash
   pm2 list
   ```

7. **Checking Logs**

After starting your application, you can check the logs using:

```bash
pm2 logs webhook-consumer
```

To view just the error logs for an application named "my-consumer":

```bash
pm2 logs webhook-consumer --err
```

To see the last 50 lines of error logs for an application with ID 0:

```bash
pm2 logs webhook-consumer --err --lines 50
```

If you want to flush logs for a specific application, you can specify the app name or ID:

```bash
pm2 flush webhook-consumer