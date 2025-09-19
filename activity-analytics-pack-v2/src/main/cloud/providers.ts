import { S3Client, PutObjectCommand, GetObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { MinioClient } from 'minio';
import OSS from 'ali-oss';
import { Readable } from 'stream';
import { features } from '../../config';

// 统一的云存储接口
export interface CloudProvider {
  uploadFile(key: string, data: Buffer | Readable): Promise<void>;
  downloadFile(key: string): Promise<Buffer>;
  listFiles(prefix: string): Promise<string[]>;
  fileExists(key: string): Promise<boolean>;
}

// MinIO 实现
export class MinioProvider implements CloudProvider {
  private client: MinioClient;
  
  constructor() {
    this.client = new MinioClient({
      endPoint: features.cloud.endpoint.replace(/^https?:\/\//, ''),
      port: features.cloud.endpoint.includes('https') ? 443 : 80,
      useSSL: features.cloud.endpoint.startsWith('https'),
      accessKey: features.cloud.accessKey,
      secretKey: features.cloud.secretKey
    });
  }
  
  async uploadFile(key: string, data: Buffer | Readable): Promise<void> {
    return new Promise((resolve, reject) => {
      const stream = Buffer.isBuffer(data) ? Readable.from(data) : data;
      
      this.client.putObject(
        features.cloud.bucket,
        key,
        stream,
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });
  }
  
  async downloadFile(key: string): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      let chunks: Buffer[] = [];
      
      this.client.getObject(features.cloud.bucket, key)
        .on('data', (chunk) => chunks.push(chunk))
        .on('end', () => resolve(Buffer.concat(chunks)))
        .on('error', (err) => reject(err));
    });
  }
  
  async listFiles(prefix: string): Promise<string[]> {
    return new Promise((resolve, reject) => {
      this.client.listObjectsV2(features.cloud.bucket, prefix, true, (err, objects) => {
        if (err) reject(err);
        else resolve(objects.map(obj => obj.name));
      });
    });
  }
  
  async fileExists(key: string): Promise<boolean> {
    try {
      const objects = await this.listFiles(key);
      return objects.some(obj => obj === key);
    } catch (error) {
      return false;
    }
  }
}

// 阿里云OSS实现
export class OSSProvider implements CloudProvider {
  private client: OSS;
  
  constructor() {
    this.client = new OSS({
      region: features.cloud.region,
      accessKeyId: features.cloud.accessKey,
      accessKeySecret: features.cloud.secretKey,
      bucket: features.cloud.bucket,
      endpoint: features.cloud.endpoint
    });
  }
  
  async uploadFile(key: string, data: Buffer | Readable): Promise<void> {
    await this.client.put(key, data);
  }
  
  async downloadFile(key: string): Promise<Buffer> {
    const result = await this.client.get(key);
    return result.content;
  }
  
  async listFiles(prefix: string): Promise<string[]> {
    const result = await this.client.list({ prefix });
    return result.objects.map(obj => obj.name);
  }
  
  async fileExists(key: string): Promise<boolean> {
    try {
      await this.client.head(key);
      return true;
    } catch (error) {
      return false;
    }
  }
}

// AWS S3实现
export class S3Provider implements CloudProvider {
  private client: S3Client;
  
  constructor() {
    this.client = new S3Client({
      region: features.cloud.region,
      endpoint: features.cloud.endpoint,
      credentials: {
        accessKeyId: features.cloud.accessKey,
        secretAccessKey: features.cloud.secretKey
      }
    });
  }
  
  async uploadFile(key: string, data: Buffer | Readable): Promise<void> {
    await this.client.send(new PutObjectCommand({
      Bucket: features.cloud.bucket,
      Key: key,
      Body: data
    }));
  }
  
  async downloadFile(key: string): Promise<Buffer> {
    const result = await this.client.send(new GetObjectCommand({
      Bucket: features.cloud.bucket,
      Key: key
    }));
    
    const body = result.Body;
    if (!body) throw new Error('Empty response body');
    
    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      body.on('data', (chunk) => chunks.push(chunk));
      body.on('end', () => resolve(Buffer.concat(chunks)));
      body.on('error', reject);
    });
  }
  
  async listFiles(prefix: string): Promise<string[]> {
    const result = await this.client.send(new ListObjectsV2Command({
      Bucket: features.cloud.bucket,
      Prefix: prefix
    }));
    
    return result.Contents?.map(item => item.Key || '') || [];
  }
  
  async fileExists(key: string): Promise<boolean> {
    try {
      const files = await this.listFiles(key);
      return files.some(file => file === key);
    } catch (error) {
      return false;
    }
  }
}

// 创建云存储实例
export function createCloudProvider(): CloudProvider {
  switch (features.cloud.provider) {
    case 'minio':
      return new MinioProvider();
    case 'oss':
      return new OSSProvider();
    case 's3':
      return new S3Provider();
    default:
      throw new Error(`不支持的云存储提供商: ${features.cloud.provider}`);
  }
}
    