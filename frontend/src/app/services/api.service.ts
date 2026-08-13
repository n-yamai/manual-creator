import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ManualImage {
  id: number;
  manual_id: number;
  image_path: string;
  timestamp: number | null;
  description: string;
  image_type?: string;
  created_at: string;
}

export interface Manual {
  id: number;
  title: string;
  content: string;
  video_path: string | null;
  created_at: string;
  updated_at: string;
  images?: ManualImage[];
}

export interface AiModel {
  id: string;
  name: string;
  description?: string;
  badge?: string;
  badgeClass?: string;
  available?: boolean;
}

export interface ApiKeyItem {
  id: string;
  label: string;
  masked_key: string;
  is_active: boolean;
}

export interface ApiKeysStatus {
  active_id: string | null;
  active_label: string | null;
  keys: ApiKeyItem[];
  using_fallback: boolean;
  fallback_masked_key: string | null;
}

export interface ApiKeyStatus {
  is_set: boolean;
  masked_key: string | null;
  using_fallback: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private get baseUrl(): string {
    // Dynamically use current hostname so external IPs/domains can connect to backend at port 3002
    const hostname = (typeof window !== 'undefined' && window.location && window.location.hostname) 
      ? window.location.hostname 
      : 'localhost';
    return `http://${hostname}:3002`;
  }

  private get apiUrl(): string {
    return `${this.baseUrl}/api`;
  }

  private get defaultOptions() {
    return { withCredentials: true };
  }

  constructor(private http: HttpClient) {}

  getModels(): Observable<AiModel[]> {
    return this.http.get<AiModel[]>(`${this.apiUrl}/models`, this.defaultOptions);
  }

  getApiKeysStatus(): Observable<ApiKeysStatus> {
    return this.http.get<ApiKeysStatus>(`${this.apiUrl}/settings/api-keys`, this.defaultOptions);
  }

  addApiKey(label: string, apiKey: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/settings/api-keys`, { label, api_key: apiKey }, this.defaultOptions);
  }

  setActiveApiKey(id: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/settings/api-keys/active`, { id }, this.defaultOptions);
  }

  deleteApiKeyItem(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/settings/api-keys/${id}`, this.defaultOptions);
  }

  getApiKeyStatus(): Observable<ApiKeyStatus> {
    return this.http.get<ApiKeyStatus>(`${this.apiUrl}/settings/api-key`, this.defaultOptions);
  }

  setApiKey(apiKey: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/settings/api-key`, { api_key: apiKey }, this.defaultOptions);
  }

  deleteApiKey(): Observable<any> {
    return this.http.delete(`${this.apiUrl}/settings/api-key`, this.defaultOptions);
  }


  getManuals(): Observable<Manual[]> {
    return this.http.get<Manual[]>(`${this.apiUrl}/manuals`, this.defaultOptions);
  }

  getManual(id: number): Observable<Manual> {
    return this.http.get<Manual>(`${this.apiUrl}/manuals/${id}`, this.defaultOptions);
  }

  updateManual(id: number, data: { title?: string; content?: string }): Observable<Manual> {
    return this.http.put<Manual>(`${this.apiUrl}/manuals/${id}`, data, this.defaultOptions);
  }

  deleteManual(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/manuals/${id}`, this.defaultOptions);
  }

  uploadVideo(file: File, promptInstruction?: string, modelName?: string): Observable<{ status: string; progress?: number; body?: Manual }> {
    const formData = new FormData();
    formData.append('file', file);
    if (promptInstruction) {
      formData.append('prompt_instruction', promptInstruction);
    }
    if (modelName) {
      formData.append('model_name', modelName);
    }

    return this.http.post<Manual>(`${this.apiUrl}/manuals/upload`, formData, {
      ...this.defaultOptions,
      reportProgress: true,
      observe: 'events'
    }).pipe(
      map(event => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            const progress = event.total ? Math.round((100 * event.loaded) / event.total) : 0;
            return { status: 'progress', progress };
          case HttpEventType.Response:
            return { status: 'completed', body: event.body as Manual };
          default:
            return { status: 'pending' };
        }
      })
    );
  }

  extractFrame(manualId: number, timestamp: number, description?: string): Observable<ManualImage> {
    return this.http.post<ManualImage>(`${this.apiUrl}/manuals/${manualId}/extract-frame`, {
      timestamp,
      description
    }, this.defaultOptions);
  }

  uploadCustomImage(manualId: number, file: File, description?: string): Observable<ManualImage> {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }
    return this.http.post<ManualImage>(`${this.apiUrl}/manuals/${manualId}/upload-image`, formData);
  }

  deleteImage(manualId: number, imageId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/manuals/${manualId}/images/${imageId}`, this.defaultOptions);
  }

  updateImage(manualId: number, imageId: number, blob: Blob): Observable<ManualImage> {
    const formData = new FormData();
    formData.append('file', blob, `edited_image_${imageId}.png`);
    return this.http.post<ManualImage>(`${this.apiUrl}/manuals/${manualId}/images/${imageId}/update`, formData, this.defaultOptions);
  }

  refineManual(manualId: number, instruction: string, currentContent: string, modelName: string = 'gemini-3.5-flash'): Observable<{ refined_content: string }> {
    return this.http.post<{ refined_content: string }>(`${this.apiUrl}/manuals/${manualId}/refine`, {
      instruction,
      current_content: currentContent,
      model_name: modelName
    }, this.defaultOptions);
  }

  getPdfUrl(id: number): string {
    return `${this.apiUrl}/manuals/${id}/pdf`;
  }

  getHtmlUrl(id: number): string {
    return `${this.apiUrl}/manuals/${id}/html`;
  }

  getMarkdownUrl(id: number): string {
    return `${this.apiUrl}/manuals/${id}/markdown`;
  }


  getMediaUrl(relativePath: string): string {
    const normalizedPath = (relativePath || '').replace(/\\/g, '/');
    const cleanPath = normalizedPath.replace(/^\/?(api\/media\/)?/, '');
    return `${this.baseUrl}/api/media/${cleanPath}`;
  }
}



