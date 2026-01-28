# File Storage Guide

## Storage Options

Your application supports **two storage backends** for uploaded files:

### 1. **Local Filesystem** (Default)
- Files stored in `uploads/` directory
- Simple setup, no external dependencies
- **Best for**: Development, small deployments
- **Limitations**: Not scalable, requires persistent disk storage

### 2. **AWS S3 / S3-Compatible** (Recommended for Production)
- Files stored in cloud storage (AWS S3, DigitalOcean Spaces, MinIO, etc.)
- Scalable, reliable, cost-effective
- **Best for**: Production, serverless deployments, high traffic
- **Benefits**: 
  - No disk space limits
  - Automatic backups
  - CDN integration
  - Better for serverless (Vercel, AWS Lambda)

### 3. **PostgreSQL (NOT Recommended)**
- ❌ **Not implemented** - Not recommended for production
- Storing files in database causes:
  - Database bloat
  - Slow queries
  - Backup/restore issues
  - Limited scalability
  - Performance problems

## Configuration

### Local Storage (Default)

No configuration needed. Files are stored in `uploads/` directory.

### S3 Storage

Add these environment variables to use S3:

```env
# Storage backend
FILE_STORAGE_BACKEND=s3

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your-bucket-name

# Optional: For S3-compatible services (DigitalOcean Spaces, MinIO, etc.)
AWS_S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com  # Example for DO Spaces
```

## S3 Setup Instructions

### AWS S3

1. **Create S3 Bucket**:
   - Go to AWS S3 Console
   - Create a new bucket
   - Choose region (e.g., `us-east-1`)
   - Set bucket name (e.g., `caa-uploads`)

2. **Create IAM User**:
   - Go to IAM Console
   - Create user with programmatic access
   - Attach policy with S3 permissions:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:PutObject",
             "s3:GetObject",
             "s3:DeleteObject"
           ],
           "Resource": "arn:aws:s3:::your-bucket-name/*"
         }
       ]
     }
     ```
   - Save Access Key ID and Secret Access Key

3. **Configure Environment Variables**:
   ```env
   FILE_STORAGE_BACKEND=s3
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-1
   AWS_S3_BUCKET_NAME=caa-uploads
   ```

### DigitalOcean Spaces (S3-Compatible)

1. **Create Space**:
   - Go to DigitalOcean → Spaces
   - Create new Space
   - Choose region and name

2. **Generate Access Keys**:
   - Go to API → Spaces Keys
   - Generate new key pair
   - Save Access Key and Secret Key

3. **Configure Environment Variables**:
   ```env
   FILE_STORAGE_BACKEND=s3
   AWS_ACCESS_KEY_ID=your-do-spaces-key
   AWS_SECRET_ACCESS_KEY=your-do-spaces-secret
   AWS_REGION=nyc3
   AWS_S3_BUCKET_NAME=your-space-name
   AWS_S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
   ```

### MinIO (Self-Hosted S3)

1. **Deploy MinIO**:
   ```bash
   docker run -p 9000:9000 -p 9001:9001 \
     -e "MINIO_ROOT_USER=minioadmin" \
     -e "MINIO_ROOT_PASSWORD=minioadmin" \
     minio/minio server /data --console-address ":9001"
   ```

2. **Create Bucket**:
   - Access MinIO Console at `http://localhost:9001`
   - Create bucket

3. **Configure Environment Variables**:
   ```env
   FILE_STORAGE_BACKEND=s3
   AWS_ACCESS_KEY_ID=minioadmin
   AWS_SECRET_ACCESS_KEY=minioadmin
   AWS_REGION=us-east-1
   AWS_S3_BUCKET_NAME=your-bucket-name
   AWS_S3_ENDPOINT_URL=http://localhost:9000
   ```

## File Storage Structure

### Local Storage
```
uploads/
  org_1/
    user_1/
      uuid-file.pdf
      uuid-image.png
    user_2/
      uuid-document.docx
  org_2/
    user_3/
      uuid-file.pdf
```

### S3 Storage
```
s3://your-bucket-name/
  org_1/
    user_1/
      uuid-file.pdf
      uuid-image.png
    user_2/
      uuid-document.docx
  org_2/
    user_3/
      uuid-file.pdf
```

## Database Schema

The `upload_files` table stores metadata:
- `file_path`: For local: file path, For S3: S3 key
- `filename`: Original filename
- `stored_filename`: Unique stored filename (UUID)
- `file_type`: MIME type
- `file_size`: File size in bytes
- `url`: Access URL (presigned for S3)

## Switching Between Storage Backends

You can switch storage backends by changing the `FILE_STORAGE_BACKEND` environment variable:

```env
# Use local storage
FILE_STORAGE_BACKEND=local

# Use S3 storage
FILE_STORAGE_BACKEND=s3
```

**Note**: Existing files won't be migrated automatically. You'll need to:
1. Download files from old storage
2. Re-upload to new storage
3. Or implement a migration script

## Production Recommendations

### For Coolify / Traditional Servers
- **Recommended**: S3 (AWS S3 or DigitalOcean Spaces)
- **Why**: Scalable, reliable, no disk space concerns

### For Serverless (Vercel, AWS Lambda)
- **Required**: S3 (local storage won't work)
- **Why**: Serverless functions have no persistent disk

### For Small Deployments
- **OK**: Local storage (if you have persistent disk)
- **Better**: S3 (for future scalability)

## Cost Comparison

### Local Storage
- **Cost**: Disk space on server
- **Scaling**: Limited by server disk
- **Backup**: Manual backup required

### AWS S3
- **Cost**: ~$0.023 per GB/month (Standard storage)
- **Scaling**: Unlimited
- **Backup**: Automatic (99.999999999% durability)

### DigitalOcean Spaces
- **Cost**: $5/month for 250GB + $0.02/GB over
- **Scaling**: Unlimited
- **Backup**: Automatic

## Security Considerations

### S3 Bucket Policies

For production, configure bucket policies to restrict access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::your-bucket-name/*",
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

This ensures files are only accessible via HTTPS.

## Troubleshooting

### S3 Connection Issues
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are correct
- Check bucket name matches exactly
- Verify IAM user has correct permissions
- Check region matches bucket region

### File Not Found
- For local: Check file path exists
- For S3: Verify S3 key is correct
- Check file permissions

### Upload Fails
- Check file size (max 50MB)
- Verify storage backend is configured correctly
- Check disk space (for local) or S3 quota (for S3)
