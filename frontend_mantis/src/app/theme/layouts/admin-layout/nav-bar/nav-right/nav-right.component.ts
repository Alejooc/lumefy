// angular import
import { Component, output, inject, input, ChangeDetectorRef, OnInit } from '@angular/core';
import { NgbDropdownModule, NgbNavModule } from '@ng-bootstrap/ng-bootstrap';
import { Notification, NotificationService } from 'src/app/core/services/notification.service';
import { RouterModule } from '@angular/router';

// project import
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { AuthService } from 'src/app/core/services/auth.service';

// third party

// icon
import { IconService } from '@ant-design/icons-angular';
import {
  BellOutline,
  SettingOutline,
  GiftOutline,
  MessageOutline,
  PhoneOutline,
  CheckCircleOutline,
  LogoutOutline,
  EditOutline,
  UserOutline,
  ProfileOutline,
  WalletOutline,
  QuestionCircleOutline,
  LockOutline,
  CommentOutline,
  UnorderedListOutline,
  ArrowRightOutline,
  GithubOutline
} from '@ant-design/icons-angular/icons';

@Component({
  selector: 'app-nav-right',
  imports: [SharedModule, RouterModule, NgbDropdownModule, NgbNavModule], // Ensure Ngb modules are imported
  templateUrl: './nav-right.component.html',
  styleUrls: ['./nav-right.component.scss']
})
export class NavRightComponent implements OnInit {
  private iconService = inject(IconService);
  private authService = inject(AuthService);
  private notificationService = inject(NotificationService);
  private cdr = inject(ChangeDetectorRef);

  currentUser$ = this.authService.currentUser;

  notifications: Notification[] = [];
  unreadCount = 0;

  // public props
  styleSelectorToggle = input<boolean>();
  readonly Customize = output();
  windowWidth: number;
  screenFull: boolean = true;
  direction: string = 'ltr';

  // constructor
  constructor() {
    this.windowWidth = window.innerWidth;
    this.iconService.addIcon(
      ...[
        CheckCircleOutline,
        GiftOutline,
        MessageOutline,
        SettingOutline,
        PhoneOutline,
        LogoutOutline,
        EditOutline,
        UserOutline,
        EditOutline,
        ProfileOutline,
        QuestionCircleOutline,
        LockOutline,
        CommentOutline,
        UnorderedListOutline,
        ArrowRightOutline,
        BellOutline,
        GithubOutline,
        WalletOutline
      ]
    );
  }

  ngOnInit() {
    this.loadNotifications();
  }

  loadNotifications() {
    this.notificationService.getUnread().subscribe({
      next: (data) => {
        this.notifications = data;
        this.unreadCount = data.length;
        this.cdr.detectChanges();
      }
    });

    // Subscribe to count updates
    this.notificationService.unreadCount$.subscribe(count => {
      this.unreadCount = count;
      this.cdr.detectChanges();
    });
  }

  markAsRead(id: string) {
    this.notificationService.markAsRead(id).subscribe(() => {
      // Update status instead of removing
      const notification = this.notifications.find(n => n.id === id);
      if (notification) {
        notification.is_read = true;
      }
      this.cdr.detectChanges();
    });
  }

  markAllRead() {
    this.notificationService.markAllAsRead().subscribe(() => {
      this.notifications = [];
      this.unreadCount = 0;
      this.cdr.detectChanges();
    });
  }

  profile = [
    {
      icon: 'edit',
      title: 'Editar Perfil',
      route: '/profile/edit'
    },
    {
      icon: 'user',
      title: 'Ver Perfil',
      route: '/profile/view'
    },
    {
      icon: 'wallet',
      title: 'Facturación',
      route: '/billing'
    },
    {
      icon: 'logout',
      title: 'Salir',
      route: null
    }
  ];

  setting = [
    {
      icon: 'question-circle',
      title: 'Support'
    },
    {
      icon: 'user',
      title: 'Account Settings'
    },
    {
      icon: 'lock',
      title: 'Privacy Center'
    },
    {
      icon: 'comment',
      title: 'Feedback'
    },
    {
      icon: 'unordered-list',
      title: 'History'
    }
  ];

  onLogout() {
    this.authService.logout();
  }
}
