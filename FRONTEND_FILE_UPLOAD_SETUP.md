# Frontend File Upload Setup Guide

This guide explains how to integrate the file upload API into your frontend application.

## API Endpoints

### Base URL
```
http://localhost:8000/api/v1/uploads  (development)
https://your-domain.com/api/v1/uploads  (production)
```

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <access_token>
```

---

## 1. Upload Files

**Endpoint:** `POST /api/v1/uploads/`

**Request:**
- Content-Type: `multipart/form-data`
- Field name: `files` (array of files)
- Max file size: 50MB per file

**Response:**
```json
{
  "files": [
    {
      "id": 1,
      "filename": "document.pdf",
      "file_type": "application/pdf",
      "file_size": 1024000,
      "uploaded_at": "2024-01-15T10:30:00Z",
      "url": "/api/v1/uploads/1/download",
      "organization_id": 1,
      "organization_name": "My Organization",
      "client_id": null
    }
  ],
  "message": "Files uploaded successfully"
}
```

### Example: React/TypeScript

```typescript
// types.ts
export interface FileResponse {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
  url: string;
  organization_id: number;
  organization_name: string | null;
  client_id: number | null;
}

export interface UploadFilesResponse {
  files: FileResponse[];
  message: string;
}

// api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadFiles(
  files: File[],
  accessToken: string
): Promise<UploadFilesResponse> {
  const formData = new FormData();
  
  // Add all files to FormData with field name "files"
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE_URL}/api/v1/uploads/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      // Don't set Content-Type header - browser will set it with boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload files');
  }

  return response.json();
}
```

### Example: React Component

```tsx
import { useState } from 'react';
import { uploadFiles } from './api';

function FileUploadComponent() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<FileResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Please select at least one file');
      return;
    }

    // Validate file sizes (50MB = 50 * 1024 * 1024 bytes)
    const maxSize = 50 * 1024 * 1024;
    const oversizedFiles = selectedFiles.filter(file => file.size > maxSize);
    
    if (oversizedFiles.length > 0) {
      setError(`Files exceed 50MB limit: ${oversizedFiles.map(f => f.name).join(', ')}`);
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const accessToken = localStorage.getItem('access_token'); // Get from your auth system
      if (!accessToken) {
        throw new Error('Not authenticated');
      }

      const response = await uploadFiles(selectedFiles, accessToken);
      setUploadedFiles(response.files);
      setSelectedFiles([]);
      alert('Files uploaded successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        multiple
        onChange={handleFileSelect}
        disabled={uploading}
      />
      <button onClick={handleUpload} disabled={uploading || selectedFiles.length === 0}>
        {uploading ? 'Uploading...' : 'Upload Files'}
      </button>
      
      {error && <div style={{ color: 'red' }}>{error}</div>}
      
      {uploadedFiles.length > 0 && (
        <div>
          <h3>Uploaded Files:</h3>
          <ul>
            {uploadedFiles.map((file) => (
              <li key={file.id}>
                {file.filename} ({formatFileSize(file.file_size)})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
```

---

## 2. List Files

**Endpoint:** `GET /api/v1/uploads/`

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records (default: 100, max: 1000)

**Response:**
```json
[
  {
    "id": 1,
    "filename": "document.pdf",
    "file_type": "application/pdf",
    "file_size": 1024000,
    "uploaded_at": "2024-01-15T10:30:00Z",
    "url": "/api/v1/uploads/1/download",
    "organization_id": 1,
    "organization_name": "My Organization",
    "client_id": null
  }
]
```

### Example: React Hook

```typescript
// hooks/useFiles.ts
import { useState, useEffect } from 'react';
import { FileResponse } from '../types';

export function useFiles(accessToken: string, skip = 0, limit = 100) {
  const [files, setFiles] = useState<FileResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchFiles() {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE_URL}/api/v1/uploads/?skip=${skip}&limit=${limit}`,
          {
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch files');
        }

        const data = await response.json();
        setFiles(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load files');
      } finally {
        setLoading(false);
      }
    }

    if (accessToken) {
      fetchFiles();
    }
  }, [accessToken, skip, limit]);

  return { files, loading, error, refetch: () => fetchFiles() };
}
```

---

## 3. Download/Preview Files

**Endpoint:** `GET /api/v1/uploads/{file_id}/download`

**Authentication:**
- Header: `Authorization: Bearer <token>` (for downloads)
- Query param: `?token=<token>` (for previews in iframe/img tags)

### Example: Download File

```typescript
export async function downloadFile(
  fileId: number,
  filename: string,
  accessToken: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/uploads/${fileId}/download`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to download file');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
```

### Example: Preview File (Image/PDF)

```tsx
// For images
<img 
  src={`${API_BASE_URL}/api/v1/uploads/${fileId}/download?token=${accessToken}`}
  alt={filename}
/>

// For PDFs
<iframe
  src={`${API_BASE_URL}/api/v1/uploads/${fileId}/download?token=${accessToken}`}
  width="100%"
  height="600px"
/>

// For any file type (using object tag)
<object
  data={`${API_BASE_URL}/api/v1/uploads/${fileId}/download?token=${accessToken}`}
  type={fileType}
  width="100%"
  height="600px"
>
  <p>Unable to display file. <a href={downloadUrl}>Download instead</a></p>
</object>
```

### Example: React Component

```tsx
function FilePreview({ fileId, filename, fileType, accessToken }: {
  fileId: number;
  filename: string;
  fileType: string;
  accessToken: string;
}) {
  const previewUrl = `${API_BASE_URL}/api/v1/uploads/${fileId}/download?token=${accessToken}`;
  const isImage = fileType.startsWith('image/');
  const isPDF = fileType === 'application/pdf';

  if (isImage) {
    return <img src={previewUrl} alt={filename} style={{ maxWidth: '100%' }} />;
  }

  if (isPDF) {
    return (
      <iframe
        src={previewUrl}
        width="100%"
        height="600px"
        title={filename}
      />
    );
  }

  return (
    <div>
      <p>Preview not available for {fileType}</p>
      <a href={previewUrl} download={filename}>
        Download {filename}
      </a>
    </div>
  );
}
```

---

## 4. Delete File

**Endpoint:** `DELETE /api/v1/uploads/{file_id}`

**Response:**
```json
{
  "message": "File deleted successfully"
}
```

### Example: React Function

```typescript
export async function deleteFile(
  fileId: number,
  accessToken: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/uploads/${fileId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete file');
  }
}
```

### Example: React Component

```tsx
function FileList({ files, accessToken, onDelete }: {
  files: FileResponse[];
  accessToken: string;
  onDelete: (fileId: number) => void;
}) {
  const handleDelete = async (fileId: number) => {
    if (!confirm('Are you sure you want to delete this file?')) {
      return;
    }

    try {
      await deleteFile(fileId, accessToken);
      onDelete(fileId);
      alert('File deleted successfully');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete file');
    }
  };

  return (
    <div>
      <h2>Uploaded Files</h2>
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.id}>
              <td>{file.filename}</td>
              <td>{formatFileSize(file.file_size)}</td>
              <td>{new Date(file.uploaded_at).toLocaleString()}</td>
              <td>
                <a
                  href={`${API_BASE_URL}${file.url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Download
                </a>
                {' '}
                <button onClick={() => handleDelete(file.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 5. Complete Example: File Manager Component

```tsx
import { useState } from 'react';
import { useFiles } from './hooks/useFiles';
import { uploadFiles, deleteFile } from './api';
import { FileResponse } from './types';

function FileManager() {
  const accessToken = localStorage.getItem('access_token');
  const { files, loading, error, refetch } = useFiles(accessToken || '');
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    if (!accessToken) {
      alert('Please login first');
      return;
    }

    setUploading(true);
    try {
      await uploadFiles(Array.from(e.target.files), accessToken);
      refetch(); // Refresh file list
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (fileId: number) => {
    if (!accessToken) return;
    if (!confirm('Delete this file?')) return;

    try {
      await deleteFile(fileId, accessToken);
      refetch(); // Refresh file list
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  if (loading) return <div>Loading files...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>File Manager</h1>
      
      <div>
        <input
          type="file"
          multiple
          onChange={handleUpload}
          disabled={uploading}
        />
        {uploading && <span>Uploading...</span>}
      </div>

      <div>
        <h2>Files ({files.length})</h2>
        <table>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Type</th>
              <th>Size</th>
              <th>Uploaded</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.id}>
                <td>{file.filename}</td>
                <td>{file.file_type}</td>
                <td>{formatFileSize(file.file_size)}</td>
                <td>{new Date(file.uploaded_at).toLocaleString()}</td>
                <td>
                  <a
                    href={`${API_BASE_URL}${file.url}?token=${accessToken}`}
                    target="_blank"
                  >
                    View
                  </a>
                  {' '}
                  <button onClick={() => handleDelete(file.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## 6. Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Authentication required. Please provide a valid access token."
}
```

**403 Forbidden:**
```json
{
  "detail": "Access denied. File does not belong to your organization."
}
```

**404 Not Found:**
```json
{
  "detail": "File not found"
}
```

**413 Payload Too Large:**
```json
{
  "detail": "File size exceeds maximum allowed size of 50MB"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to upload files: <error message>"
}
```

### Error Handling Example

```typescript
async function handleApiError(response: Response): Promise<never> {
  let errorMessage = 'An error occurred';
  
  try {
    const error = await response.json();
    errorMessage = error.detail || errorMessage;
  } catch {
    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
  }

  throw new Error(errorMessage);
}

// Usage
try {
  const response = await fetch(url, options);
  if (!response.ok) {
    await handleApiError(response);
  }
  return await response.json();
} catch (error) {
  console.error('API Error:', error);
  // Show user-friendly error message
  alert(error instanceof Error ? error.message : 'Something went wrong');
  throw error;
}
```

---

## 7. Environment Configuration

### .env.local (Next.js) or .env (React)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# or for production:
# NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

### Config File

```typescript
// config.ts
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  maxFileSize: 50 * 1024 * 1024, // 50MB
  allowedFileTypes: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    // Add more as needed
  ],
};
```

---

## 8. Upload Progress (Optional)

For large files, you can track upload progress:

```typescript
export async function uploadFilesWithProgress(
  files: File[],
  accessToken: string,
  onProgress?: (progress: number) => void
): Promise<UploadFilesResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('POST', `${API_BASE_URL}/api/v1/uploads/`);
    xhr.setRequestHeader('Authorization', `Bearer ${accessToken}`);
    xhr.send(formData);
  });
}
```

---

## 9. Notes

1. **File Size Limit**: Maximum 50MB per file
2. **Multiple Files**: You can upload multiple files in a single request
3. **File Organization**: Files are automatically organized by organization and user
4. **S3 Storage**: If using S3, files are stored in the structure: `org_{org_id}/user_{user_id}/{filename}`
5. **Token Expiration**: Make sure to handle token expiration and refresh tokens
6. **CORS**: Ensure your backend CORS settings allow your frontend origin
7. **Preview Support**: Use query parameter `?token=...` for previews in iframe/img tags

---

## 10. Testing

### Test Upload
```bash
curl -X POST http://localhost:8000/api/v1/uploads/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@/path/to/file1.pdf" \
  -F "files=@/path/to/file2.jpg"
```

### Test List
```bash
curl http://localhost:8000/api/v1/uploads/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Download
```bash
curl http://localhost:8000/api/v1/uploads/1/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o downloaded_file.pdf
```

### Test Delete
```bash
curl -X DELETE http://localhost:8000/api/v1/uploads/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```
