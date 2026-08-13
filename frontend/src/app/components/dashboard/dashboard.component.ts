import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { ApiService, Manual } from '../../services/api.service';
import { ApiKeyModalComponent } from '../api-key-modal/api-key-modal.component';
import { 
  LucideAngularModule, 
  Plus, 
  FileText, 
  Trash2, 
  Edit3, 
  Download,
  Calendar,
  Clock,
  Video,
  LayoutDashboard,
  Search,
  Sparkles,
  BookOpen,
  Key
} from 'lucide-angular';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, LucideAngularModule, ApiKeyModalComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  manuals: Manual[] = [];
  filteredManuals: Manual[] = [];
  recentManuals: Manual[] = [];
  searchQuery = '';
  loading = true;
  error = '';
  isApiKeyModalOpen = false;
  activeKeyLabel: string | null = null;

  // Icons
  PlusIcon = Plus;
  FileTextIcon = FileText;
  TrashIcon = Trash2;
  EditIcon = Edit3;
  DownloadIcon = Download;
  CalendarIcon = Calendar;
  ClockIcon = Clock;
  VideoIcon = Video;
  DashboardIcon = LayoutDashboard;
  SearchIcon = Search;
  SparklesIcon = Sparkles;
  BookOpenIcon = BookOpen;
  KeyIcon = Key;


  constructor(private apiService: ApiService, private router: Router) {}

  ngOnInit(): void {
    this.loadManuals();
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

  loadManuals(): void {

    this.loading = true;
    this.apiService.getManuals().subscribe({
      next: (data) => {
        this.manuals = data;
        this.filteredManuals = data;
        this.recentManuals = data.slice(0, 5);
        this.loading = false;
      },

      error: (err) => {
        this.error = '手順書の読み込みに失敗しました。バックエンドサーバーが起動しているか確認してください。';
        this.loading = false;
        console.error(err);
      }
    });
  }

  filterManuals(event: any): void {
    const query = event.target.value.toLowerCase();
    this.searchQuery = query;
    if (!query) {
      this.filteredManuals = this.manuals;
    } else {
      this.filteredManuals = this.manuals.filter(m => 
        m.title.toLowerCase().includes(query) || 
        (m.content && m.content.toLowerCase().includes(query))
      );
    }
  }


  deleteManual(id: number, event: Event): void {
    event.stopPropagation();
    if (confirm('本当にこの手順書を削除しますか？関連する動画や画像も削除されます。')) {
      this.apiService.deleteManual(id).subscribe({
        next: () => {
          this.loadManuals();
        },
        error: (err) => {
          alert('削除に失敗しました。');
          console.error(err);
        }
      });
    }
  }

  downloadPdf(id: number, event: Event): void {
    event.stopPropagation();
    window.open(this.apiService.getPdfUrl(id), '_blank');
  }

  navigateToEditor(id: number): void {
    this.router.navigate(['/edit', id]);
  }
}
