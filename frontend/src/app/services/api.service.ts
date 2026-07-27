import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface ManualImage {
  id: number;
  manual_id: number;
  image_path: string;
  timestamp: number;
  description: string;
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



  constructor(private http: HttpClient) {}

  getManuals(): Observable<Manual[]> {
    return this.http.get<Manual[]>(`${this.apiUrl}/manuals`);
  }

  getManual(id: number): Observable<Manual> {
    return this.http.get<Manual>(`${this.apiUrl}/manuals/${id}`);
  }

  updateManual(id: number, data: { title?: string; content?: string }): Observable<Manual> {
    return this.http.put<Manual>(`${this.apiUrl}/manuals/${id}`, data);
  }

  deleteManual(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/manuals/${id}`);
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
    });
  }

  deleteImage(manualId: number, imageId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/manuals/${manualId}/images/${imageId}`);
  }

  updateImage(manualId: number, imageId: number, blob: Blob): Observable<ManualImage> {
    const formData = new FormData();
    formData.append('file', blob, `edited_image_${imageId}.png`);
    return this.http.post<ManualImage>(`${this.apiUrl}/manuals/${manualId}/images/${imageId}/update`, formData);
  }

  refineManual(manualId: number, instruction: string, currentContent: string, modelName: string = 'gemini-3.5-flash'): Observable<{ refined_content: string }> {
    return this.http.post<{ refined_content: string }>(`${this.apiUrl}/manuals/${manualId}/refine`, {
      instruction,
      current_content: currentContent,
      model_name: modelName
    });
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
    // Backend StaticFiles mounts media_dir at /api/media
    // relativePath is stored as "images/filename.png" or "videos/filename.mp4"
    const cleanPath = relativePath.replace(/^\/?(api\/media\/)?/, '');
    return `${this.baseUrl}/api/media/${cleanPath}`;
  }

}
