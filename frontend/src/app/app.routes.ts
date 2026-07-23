import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { ManualCreatorComponent } from './components/manual-creator/manual-creator.component';
import { ManualEditorComponent } from './components/manual-editor/manual-editor.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'create', component: ManualCreatorComponent },
  { path: 'edit/:id', component: ManualEditorComponent },
  { path: '**', redirectTo: '' }
];

