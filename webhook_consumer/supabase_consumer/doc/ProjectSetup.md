# Project Setup

## 1. Create Project Structure

```bash
mkdir webhook-consumer
cd webhook-consumer
npm init -y
```

## 2. Install Dependencies

```bash
npm install @supabase/supabase-js pg dotenv punycode
npm install --save-dev @types/pg typescript ts-node @types/node @swc/core @swc/cli
```

## 3. Configure Project

Create `package.json`:

```json
{
  "name": "webhook-consumer",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
      "dev": "swc src -d dist --watch",
      "build": "swc src -d dist",
      "start": "node dist/consumer.js"
    }
}
```

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true
  }
}
```

## 4. Configure swc

Create `.swcrc`:

```json
{
  "jsc": {
    "parser": {
      "syntax": "typescript",
      "decorators": true
    },
    "transform": {
      "legacyDecorator": true,
      "decoratorMetadata": true
    },
    "target": "es2020"
  },
  "module": {
    "type": "es6"
  },
  "sourceMaps": false  
}
```

### 5. Create Environment File

Create `.env`:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
POSTGRESQL_HOST=postgresql_url
```

### 3. Run Local Consumer

```bash
npm start
```
