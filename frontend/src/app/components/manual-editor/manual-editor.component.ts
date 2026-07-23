import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService, Manual, ManualImage } from '../../services/api.service';
import { MarkdownModule } from 'ngx-markdown';
import { 
  LucideAngularModule, 
  ArrowLeft, 
  Save, 
  Download, 
  FileText, 
  Code, 
  Video, 
  Play, 
  Image as ImageIcon,
  Check,
  Eye,
  Edit2,
  Camera,
  Plus,
  Trash2,
  ChevronDown,
  FileCode,
  Pause,
  RotateCcw,
  RotateCw,
  Crop,
  Square,
  Circle,
  MoveRight,
  Maximize2,
  Undo2,
  X
} from 'lucide-angular';




@Component({
  selector: 'app-manual-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MarkdownModule, LucideAngularModule],
  templateUrl: './manual-editor.component.html',
  styleUrls: ['./manual-editor.component.css']
})
export class ManualEditorComponent implements OnInit {
  manualId!: number;
  manual!: Manual;
  loading = true;
  saving = false;
  saveSuccess = false;
  isExtracting = false;
  error = '';
  
  // Tab control (useful on mobile/tablet)
  activeTab: 'edit' | 'preview' = 'edit';
  
  @ViewChild('videoPlayer') videoPlayer!: ElementRef<HTMLVideoElement>;

  // Icons
  ArrowLeftIcon = ArrowLeft;
  SaveIcon = Save;
  DownloadIcon = Download;
  FileTextIcon = FileText;
  CodeIcon = Code;
  VideoIcon = Video;
  PlayIcon = Play;
  ImageIcon = ImageIcon;
  CheckIcon = Check;
  EyeIcon = Eye;
  EditIcon = Edit2;
  CameraIcon = Camera;
  PlusIcon = Plus;
  TrashIcon = Trash2;
  ChevronDownIcon = ChevronDown;
  FileCodeIcon = FileCode;
  PauseIcon = Pause;
  RotateCcwIcon = RotateCcw;
  RotateCwIcon = RotateCw;

  videoDuration = 0;
  videoCurrentTime = 0;
  isPlaying = false;

  onVideoLoadedMetadata(): void {
    if (this.videoPlayer && this.videoPlayer.nativeElement) {
      this.videoDuration = this.videoPlayer.nativeElement.duration || 0;
    }
  }

  onVideoTimeUpdate(): void {
    if (this.videoPlayer && this.videoPlayer.nativeElement) {
      this.videoCurrentTime = this.videoPlayer.nativeElement.currentTime || 0;
    }
  }

  onVideoPlay(): void {
    this.isPlaying = true;
  }

  onVideoPause(): void {
    this.isPlaying = false;
  }

  togglePlay(): void {
    if (!this.videoPlayer || !this.videoPlayer.nativeElement) return;
    const video = this.videoPlayer.nativeElement;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }

  onSliderSeek(event: Event): void {
    const target = event.target as HTMLInputElement;
    const seconds = parseFloat(target.value);
    if (!isNaN(seconds)) {
      this.seekTo(seconds);
    }
  }

  skipSeconds(seconds: number): void {
    if (!this.videoPlayer || !this.videoPlayer.nativeElement) return;
    const newTime = Math.max(0, Math.min(this.videoDuration, this.videoCurrentTime + seconds));
    this.seekTo(newTime);
  }




  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.manualId = parseInt(idParam, 10);
      this.loadManual();
    } else {
      this.error = '無効な手順書IDです。';
      this.loading = false;
    }
  }

  loadManual(): void {
    this.loading = true;
    this.apiService.getManual(this.manualId).subscribe({
      next: (data) => {
        this.manual = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = '手順書の読み込みに失敗しました。バックエンドサーバーとの通信を確認してください。';
        this.loading = false;
        console.error(err);
      }
    });
  }

  saveManual(): void {
    this.saving = true;
    this.saveSuccess = false;
    this.apiService.updateManual(this.manualId, {
      title: this.manual.title,
      content: this.manual.content
    }).subscribe({
      next: (updated) => {
        this.manual.title = updated.title;
        this.manual.content = updated.content;
        this.saving = false;
        this.saveSuccess = true;
        setTimeout(() => this.saveSuccess = false, 3000);
      },
      error: (err) => {
        alert('保存に失敗しました。');
        this.saving = false;
        console.error(err);
      }
    });
  }

  // Seek video to specific timestamp (seconds) and play
  seekTo(seconds: number): void {
    if (this.videoPlayer && this.videoPlayer.nativeElement) {
      this.videoPlayer.nativeElement.currentTime = seconds;
      this.videoPlayer.nativeElement.play();
      
      // Scroll to video player for mobile usability
      this.videoPlayer.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  getVideoUrl(): string {
    if (!this.manual || !this.manual.video_path) return '';
    const videoPath = this.manual.video_path;
    const filename = videoPath.substring(videoPath.lastIndexOf('/') + 1);
    return this.apiService.getMediaUrl(`videos/${filename}`);
  }

  getAbsoluteImageUrl(relativePath: string): string {
    return this.apiService.getMediaUrl(relativePath);
  }

  downloadPdf(): void {
    window.open(this.apiService.getPdfUrl(this.manualId), '_blank');
  }

  downloadHtml(): void {
    window.open(this.apiService.getHtmlUrl(this.manualId), '_blank');
  }

  downloadMarkdown(): void {
    window.open(this.apiService.getMarkdownUrl(this.manualId), '_blank');
  }

  // Formats markdown content for preview: fixes relative image URLs and unreplaced placeholders
  getFormattedContent(): string {
    if (!this.manual || !this.manual.content) {
      return '';
    }

    let content = this.manual.content;

    // 1. Fix relative paths like /api/media/... or images/... to full http://localhost:3002/api/media/...
    content = content.replace(
      /!\[([^\]]*)\]\((?:\/api\/media\/|images\/|http:\/\/localhost:3002\/api\/media\/)?([^)]+)\)/g,
      (match, alt, filename) => {
        const cleanFilename = filename.split('/').pop();
        const fullUrl = this.apiService.getMediaUrl(`images/${cleanFilename}`);
        return `![${alt}](${fullUrl})`;
      }
    );

    // 2. Fallback for any unreplaced index placeholders like ![image](0)
    const images = this.manual.images;
    if (images && images.length > 0) {
      content = content.replace(
        /!\s*\[([^\]]*)\]\s*\(\s*(\d+)\s*\)/g,
        (match, alt, indexStr) => {
          const idx = parseInt(indexStr, 10);
          if (idx < images.length) {
            const img = images[idx];
            const fullUrl = this.getAbsoluteImageUrl(img.image_path);
            return `![${alt || img.description || '静止画'}](${fullUrl})`;
          }
          return match;
        }
      );
    }


    return content;
  }


  // Extract current video frame as a new image
  extractCurrentFrame(): void {
    if (!this.videoPlayer || !this.videoPlayer.nativeElement) return;
    
    const timestamp = this.videoPlayer.nativeElement.currentTime;
    if (timestamp === undefined || timestamp < 0) return;

    this.isExtracting = true;
    const desc = `静止画 (${timestamp.toFixed(1)}秒)`;

    this.apiService.extractFrame(this.manualId, timestamp, desc).subscribe({
      next: (newImage) => {
        if (!this.manual.images) {
          this.manual.images = [];
        }
        this.manual.images.push(newImage);
        this.isExtracting = false;
      },
      error: (err) => {
        alert('静止画の切り出しに失敗しました。');
        this.isExtracting = false;
        console.error(err);
      }
    });
  }

  // Insert image markdown tag into editor text
  insertImageToEditor(img: ManualImage, event: Event): void {
    event.stopPropagation();
    const imgUrl = this.getAbsoluteImageUrl(img.image_path);
    const markdownTag = `\n\n![${img.description || '静止画'}](${imgUrl})\n\n`;
    this.manual.content = (this.manual.content || '') + markdownTag;
  }

  // Delete specific extracted image
  deleteImage(img: ManualImage, event: Event): void {
    event.stopPropagation();
    if (confirm('この切り出し画像を削除しますか？')) {
      this.apiService.deleteImage(this.manualId, img.id).subscribe({
        next: () => {
          this.manual.images = (this.manual.images || []).filter(i => i.id !== img.id);
        },
        error: (err) => {
          alert('画像の削除に失敗しました。');
          console.error(err);
        }
      });
    }
  }

  // --- Image Editor Modal Logic ---
  @ViewChild('editorCanvas') editorCanvas!: ElementRef<HTMLCanvasElement>;
  isImageEditorOpen = false;
  editingImage: ManualImage | null = null;
  selectedTool: 'crop' | 'rect' | 'circle' | 'arrow' = 'rect';
  selectedColor = '#ef4444'; // Default Red
  selectedLineWidth = 4;
  isSavingEditedImage = false;
  cropSelected = false;

  CropIcon = Crop;
  SquareIcon = Square;
  CircleIcon = Circle;
  ArrowIcon = MoveRight;
  UndoIcon = Undo2;
  CloseIcon = X;

  colorOptions = [
    { name: '赤', value: '#ef4444' },
    { name: '青', value: '#0050cb' },
    { name: '黄', value: '#f59e0b' },
    { name: '緑', value: '#10b981' },
    { name: '白', value: '#ffffff' },
    { name: '黒', value: '#1e293b' }
  ];

  lineWidthOptions = [
    { label: '細 (2px)', value: 2 },
    { label: '標準 (4px)', value: 4 },
    { label: '太 (8px)', value: 8 }
  ];

  private canvasCtx: CanvasRenderingContext2D | null = null;
  private loadedImgElement: HTMLImageElement | null = null;
  private isDrawing = false;
  private startX = 0;
  private startY = 0;
  private currentX = 0;
  private currentY = 0;
  private historyStack: ImageData[] = [];

  openImageEditor(img: ManualImage, event: Event): void {
    event.stopPropagation();
    this.editingImage = img;
    this.isImageEditorOpen = true;
    this.historyStack = [];
    this.cropSelected = false;
    this.selectedTool = 'rect';

    const fullUrl = this.getAbsoluteImageUrl(img.image_path) + '?t=' + new Date().getTime();
    setTimeout(() => {
      this.initCanvasWithImage(fullUrl);
    }, 100);
  }

  closeImageEditor(): void {
    this.isImageEditorOpen = false;
    this.editingImage = null;
    this.historyStack = [];
  }

  initCanvasWithImage(imgUrl: string): void {
    if (!this.editorCanvas) return;
    const canvas = this.editorCanvas.nativeElement;
    this.canvasCtx = canvas.getContext('2d');

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      this.loadedImgElement = img;
      // Max dimensions for editor
      const maxWidth = 800;
      const maxHeight = 600;
      let width = img.width;
      let height = img.height;

      if (width > maxWidth) {
        height = Math.round((height * maxWidth) / width);
        width = maxWidth;
      }
      if (height > maxHeight) {
        width = Math.round((width * maxHeight) / height);
        height = maxHeight;
      }

      canvas.width = width;
      canvas.height = height;

      if (this.canvasCtx) {
        this.canvasCtx.drawImage(img, 0, 0, width, height);
        this.saveCanvasState();
      }
    };
    img.src = imgUrl;
  }

  saveCanvasState(): void {
    if (this.canvasCtx && this.editorCanvas) {
      const canvas = this.editorCanvas.nativeElement;
      const imageData = this.canvasCtx.getImageData(0, 0, canvas.width, canvas.height);
      this.historyStack.push(imageData);
    }
  }

  undoCanvas(): void {
    if (this.historyStack.length > 1) {
      this.historyStack.pop(); // Remove current
      const prevState = this.historyStack[this.historyStack.length - 1];
      if (this.canvasCtx && this.editorCanvas) {
        const canvas = this.editorCanvas.nativeElement;
        canvas.width = prevState.width;
        canvas.height = prevState.height;
        this.canvasCtx.putImageData(prevState, 0, 0);
      }
      this.cropSelected = false;
    }
  }

  resetCanvas(): void {
    if (this.editingImage) {
      const fullUrl = this.getAbsoluteImageUrl(this.editingImage.image_path) + '?t=' + new Date().getTime();
      this.historyStack = [];
      this.cropSelected = false;
      this.initCanvasWithImage(fullUrl);
    }
  }

  onCanvasMouseDown(event: MouseEvent): void {
    if (!this.canvasCtx || !this.editorCanvas) return;
    const rect = this.editorCanvas.nativeElement.getBoundingClientRect();
    this.startX = event.clientX - rect.left;
    this.startY = event.clientY - rect.top;
    this.isDrawing = true;
  }

  onCanvasMouseMove(event: MouseEvent): void {
    if (!this.isDrawing || !this.canvasCtx || !this.editorCanvas) return;
    const rect = this.editorCanvas.nativeElement.getBoundingClientRect();
    this.currentX = event.clientX - rect.left;
    this.currentY = event.clientY - rect.top;

    // Restore last state before previewing drag
    if (this.historyStack.length > 0) {
      this.canvasCtx.putImageData(this.historyStack[this.historyStack.length - 1], 0, 0);
    }

    // Preview current shape/crop box
    this.drawPreview(this.canvasCtx, this.startX, this.startY, this.currentX, this.currentY);
  }

  onCanvasMouseUp(event: MouseEvent): void {
    if (!this.isDrawing || !this.canvasCtx || !this.editorCanvas) return;
    this.isDrawing = false;
    const rect = this.editorCanvas.nativeElement.getBoundingClientRect();
    this.currentX = event.clientX - rect.left;
    this.currentY = event.clientY - rect.top;

    if (this.selectedTool === 'crop') {
      const cropW = Math.abs(this.currentX - this.startX);
      const cropH = Math.abs(this.currentY - this.startY);
      if (cropW > 10 && cropH > 10) {
        this.cropSelected = true;
      }
    } else {
      // Commit drawn shape into history
      this.saveCanvasState();
    }
  }

  private drawPreview(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number): void {
    if (this.selectedTool === 'crop') {
      // Draw selection dashed box
      ctx.save();
      ctx.setLineDash([6, 6]);
      ctx.strokeStyle = '#0050cb';
      ctx.lineWidth = 2;
      const x = Math.min(x1, x2);
      const y = Math.min(y1, y2);
      const w = Math.abs(x2 - x1);
      const h = Math.abs(y2 - y1);
      ctx.strokeRect(x, y, w, h);
      ctx.restore();
    } else {
      this.drawShape(ctx, x1, y1, x2, y2, this.selectedTool, this.selectedColor, this.selectedLineWidth);
    }
  }

  private drawShape(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number, tool: string, color: string, width: number): void {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    const minX = Math.min(x1, x2);
    const minY = Math.min(y1, y2);
    const w = Math.abs(x2 - x1);
    const h = Math.abs(y2 - y1);

    if (tool === 'rect') {
      ctx.strokeRect(minX, minY, w, h);
    } else if (tool === 'circle') {
      ctx.beginPath();
      ctx.ellipse(minX + w / 2, minY + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
      ctx.stroke();
    } else if (tool === 'arrow') {
      // Draw line
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Draw arrowhead at (x2, y2)
      const headLength = Math.max(12, width * 3);
      const angle = Math.atan2(y2 - y1, x2 - x1);

      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - headLength * Math.cos(angle - Math.PI / 6), y2 - headLength * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(x2 - headLength * Math.cos(angle + Math.PI / 6), y2 - headLength * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
    }

    ctx.restore();
  }

  applyCrop(): void {
    if (!this.canvasCtx || !this.editorCanvas || !this.cropSelected) return;
    const canvas = this.editorCanvas.nativeElement;
    const x = Math.min(this.startX, this.currentX);
    const y = Math.min(this.startY, this.currentY);
    const w = Math.abs(this.currentX - this.startX);
    const h = Math.abs(this.currentY - this.startY);

    if (w < 10 || h < 10) return;

    // Crop current image data
    const croppedData = this.canvasCtx.getImageData(x, y, w, h);

    // Resize canvas
    canvas.width = w;
    canvas.height = h;

    this.canvasCtx.putImageData(croppedData, 0, 0);
    this.cropSelected = false;
    this.saveCanvasState();
  }

  saveEditedImage(): void {
    if (!this.editorCanvas || !this.editingImage) return;
    this.isSavingEditedImage = true;
    const canvas = this.editorCanvas.nativeElement;

    canvas.toBlob((blob) => {
      if (!blob || !this.editingImage) {
        this.isSavingEditedImage = false;
        alert('画像の取得に失敗しました。');
        return;
      }

      this.apiService.updateImage(this.manualId, this.editingImage.id, blob).subscribe({
        next: (updatedImage) => {
          this.isSavingEditedImage = false;
          this.closeImageEditor();

          // Update image in local manual state with cache buster
          if (this.manual.images) {
            const idx = this.manual.images.findIndex(i => i.id === updatedImage.id);
            if (idx !== -1) {
              this.manual.images[idx] = updatedImage;
            }
          }
        },
        error: (err) => {
          this.isSavingEditedImage = false;
          alert('画像の保存に失敗しました。');
          console.error(err);
        }
      });
    }, 'image/png');
  }

}

