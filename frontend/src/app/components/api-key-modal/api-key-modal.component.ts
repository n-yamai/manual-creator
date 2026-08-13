import { Component, EventEmitter, Input, OnInit, Output, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, ApiKeysStatus, ApiKeyItem } from '../../services/api.service';
import { 
  LucideAngularModule, 
  Key, 
  Eye, 
  EyeOff, 
  CheckCircle2, 
  AlertCircle, 
  Trash2, 
  X,
  ShieldCheck,
  Plus,
  Check,
  Tag
} from 'lucide-angular';

@Component({
  selector: 'app-api-key-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './api-key-modal.component.html',
  styleUrls: ['./api-key-modal.component.css']
})
export class ApiKeyModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() statusChanged = new EventEmitter<void>();

  keyLabelInput = '';
  apiKeyInput = '';
  showPassword = false;
  isLoading = false;
  isSaving = false;
  isOperatingId: string | null = null;
  errorMessage = '';
  successMessage = '';

  keysStatus: ApiKeysStatus = {
    active_id: null,
    active_label: null,
    keys: [],
    using_fallback: false,
    fallback_masked_key: null
  };

  // Icons
  KeyIcon = Key;
  EyeIcon = Eye;
  EyeOffIcon = EyeOff;
  CheckCircleIcon = CheckCircle2;
  AlertIcon = AlertCircle;
  TrashIcon = Trash2;
  CloseIcon = X;
  ShieldIcon = ShieldCheck;
  PlusIcon = Plus;
  CheckIcon = Check;
  TagIcon = Tag;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    if (this.isOpen) {
      this.loadStatus();
    }
  }

  ngOnChanges(): void {
    if (this.isOpen) {
      this.loadStatus();
    }
  }

  loadStatus(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.apiService.getApiKeysStatus().subscribe({
      next: (res) => {
        this.keysStatus = res;
        this.isLoading = false;
      },
      error: (err) => {
        console.error(err);
        this.isLoading = false;
      }
    });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  addKey(): void {
    if (!this.apiKeyInput.trim()) {
      this.errorMessage = 'APIキーを入力してください。';
      return;
    }

    const label = this.keyLabelInput.trim() || `キー #${this.keysStatus.keys.length + 1}`;

    this.isSaving = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.apiService.addApiKey(label, this.apiKeyInput.trim()).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.apiKeyInput = '';
        this.keyLabelInput = '';
        this.successMessage = `APIキー「${label}」を登録し、有効化しました！`;
        this.loadStatus();
        this.statusChanged.emit();
      },
      error: (err) => {
        this.isSaving = false;
        const apiDetail = err.error?.detail;
        if (apiDetail) {
          this.errorMessage = apiDetail;
        } else {
          this.errorMessage = 'APIキーの検証に失敗しました。キーに間違いがないかご確認ください。';
        }
      }
    });
  }

  setActiveKey(keyItem: ApiKeyItem): void {
    if (keyItem.is_active) return;

    this.isOperatingId = keyItem.id;
    this.errorMessage = '';
    this.successMessage = '';

    this.apiService.setActiveApiKey(keyItem.id).subscribe({
      next: () => {
        this.isOperatingId = null;
        this.successMessage = `「${keyItem.label}」に切り替えました。`;
        this.loadStatus();
        this.statusChanged.emit();
      },
      error: (err) => {
        this.isOperatingId = null;
        this.errorMessage = 'APIキーの切り替えに失敗しました。';
      }
    });
  }

  deleteKeyItem(keyItem: ApiKeyItem, event: Event): void {
    event.stopPropagation();
    if (!confirm(`APIキー「${keyItem.label}」を削除しますか？`)) {
      return;
    }

    this.isOperatingId = keyItem.id;
    this.errorMessage = '';
    this.successMessage = '';

    this.apiService.deleteApiKeyItem(keyItem.id).subscribe({
      next: () => {
        this.isOperatingId = null;
        this.successMessage = `APIキー「${keyItem.label}」を削除しました。`;
        this.loadStatus();
        this.statusChanged.emit();
      },
      error: (err) => {
        this.isOperatingId = null;
        this.errorMessage = 'APIキーの削除に失敗しました。';
      }
    });
  }

  closeModal(): void {
    this.errorMessage = '';
    this.successMessage = '';
    this.apiKeyInput = '';
    this.keyLabelInput = '';
    this.close.emit();
  }
}
