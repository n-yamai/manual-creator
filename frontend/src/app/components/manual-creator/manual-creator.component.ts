import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ApiService, Manual } from '../../services/api.service';
import { ApiKeyModalComponent } from '../api-key-modal/api-key-modal.component';
import { 
  LucideAngularModule, 
  ArrowLeft, 
  Upload, 
  Sparkles, 
  AlertCircle,
  FileVideo,
  CheckCircle2,
  LayoutDashboard,
  Plus,
  FileText,
  Key
} from 'lucide-angular';

@Component({
  selector: 'app-manual-creator',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LucideAngularModule, ApiKeyModalComponent],
  templateUrl: './manual-creator.component.html',
  styleUrls: ['./manual-creator.component.css']
})
export class ManualCreatorComponent implements OnInit {
  selectedFile: File | null = null;
  promptInstruction = '';
  selectedModel = 'gemini-3.5-flash';
  uploadProgress = 0;
  isUploading = false;
  isGenerating = false;
  errorMessage = '';
  recentManuals: Manual[] = [];
  isApiKeyModalOpen = false;
  isLoadingModels = false;

  aiModels: any[] = [
    {
      id: 'gemini-3.5-flash',
      name: 'Gemini 3.5 Flash',
      badge: '推奨 (標準)',
      badgeClass: 'badge-recommended',
      description: '高速かつバランスの取れた標準モデル。画像・音声の高品質なステップ解析を行います。',
      available: true
    },
    {
      id: 'gemini-3.6-flash',
      name: 'Gemini 3.6 Flash',
      badge: '最新 Flash',
      badgeClass: 'badge-new',
      description: '最新フラグシップ Flash モデル。高度で精度の高い理解能力を備えます。',
      available: true
    },
    {
      id: 'gemini-3.5-flash-lite',
      name: 'Gemini 3.5 Flash Lite',
      badge: '超高速',
      badgeClass: 'badge-lite',
      description: '処理スピード最優先の軽量モデル。迅速にドラフト作成したい場合に最適です。',
      available: true
    },
    {
      id: 'gemini-3-pro-preview',
      name: 'Gemini 3 Pro Preview',
      badge: '高精度 Pro',
      badgeClass: 'badge-pro',
      description: '深い推論と複雑な手順解析が可能な最高精度 Pro モデル。',
      available: true
    },
    {
      id: 'gemini-2.5-pro',
      name: 'Gemini 2.5 Pro',
      badge: 'Pro 安定版',
      badgeClass: 'badge-pro',
      description: '安定性に優れた Pro グレードモデル。',
      available: true
    }
  ];

  // Icons
  ArrowLeftIcon = ArrowLeft;
  UploadIcon = Upload;
  SparklesIcon = Sparkles;
  AlertIcon = AlertCircle;
  VideoFileIcon = FileVideo;
  CheckIcon = CheckCircle2;
  DashboardIcon = LayoutDashboard;
  PlusIcon = Plus;
  FileTextIcon = FileText;
  KeyIcon = Key;
  activeKeyLabel: string | null = null;

  constructor(private apiService: ApiService, private router: Router) {}

  ngOnInit(): void {
    this.apiService.getManuals().subscribe({
      next: (data) => this.recentManuals = data.slice(0, 5),
      error: (err) => console.error(err)
    });
    this.loadModels();
    this.loadKeyStatus();
  }

  loadKeyStatus(): void {
    this.apiService.getApiKeysStatus().subscribe({
      next: (res) => {
        this.activeKeyLabel = res.active_label || (res.keys && res.keys.length > 0 ? res.keys[0].label : null);
      },
      error: () => {}
    });
  }

  onKeyStatusChanged(): void {
    this.loadModels();
    this.loadKeyStatus();
  }

  loadModels(): void {
    this.isLoadingModels = true;
    this.apiService.getModels().subscribe({
      next: (models) => {
        this.isLoadingModels = false;
        if (models && models.length > 0) {
          this.aiModels = models;
          const currentObj = this.aiModels.find(m => m.id === this.selectedModel);
          if (!currentObj || currentObj.available === false) {
            const firstAvailable = this.aiModels.find(m => m.available !== false);
            if (firstAvailable) {
              this.selectedModel = firstAvailable.id;
            }
          }
        }
      },
      error: (err) => {
        this.isLoadingModels = false;
        console.error('Failed to load models:', err);
      }
    });
  }

  selectModel(modelId: string, available?: boolean): void {
    if (available === false) return;
    this.selectedModel = modelId;
  }



  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.errorMessage = '';
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const file = event.dataTransfer?.files[0];
    if (file && file.type.startsWith('video/')) {
      this.selectedFile = file;
      this.errorMessage = '';
    } else {
      this.errorMessage = '動画ファイル (MP4, MOV など) をドラッグ＆ドロップしてください。';
    }
  }

  generateManual(): void {
    if (!this.selectedFile) {
      this.errorMessage = '動画ファイルを選択してください。';
      return;
    }

    this.isUploading = true;
    this.uploadProgress = 0;
    this.errorMessage = '';

    this.apiService.uploadVideo(this.selectedFile, this.promptInstruction, this.selectedModel).subscribe({
      next: (res) => {
        if (res.status === 'progress') {
          this.uploadProgress = res.progress || 0;
          if (this.uploadProgress === 100) {
            this.isUploading = false;
            this.isGenerating = true; // Video uploaded, now AI is generating
          }
        } else if (res.status === 'completed' && res.body) {
          this.isGenerating = false;
          this.router.navigate(['/edit', res.body.id]);
        }
      },
      error: (err) => {
        this.isUploading = false;
        this.isGenerating = false;
        const apiDetail = err.error?.detail;
        if (apiDetail && typeof apiDetail === 'string') {
          this.errorMessage = apiDetail;
        } else {
          this.errorMessage = '手順書の生成中にエラーが発生しました。ネットワーク接続やAPIキー設定をご確認ください。';
        }
        console.error(err);
      }

    });
  }
}
