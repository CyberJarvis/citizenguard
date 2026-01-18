# CoastGuardians Flutter Mobile App Guide
## Citizen-Side Mobile Application for iOS & Android

**Version:** 1.0
**Last Updated:** December 1, 2025

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites & Setup](#2-prerequisites--setup)
3. [Project Structure](#3-project-structure)
4. [Dependencies (pubspec.yaml)](#4-dependencies-pubspecyaml)
5. [API Configuration](#5-api-configuration)
6. [Data Models](#6-data-models)
7. [API Service Layer](#7-api-service-layer)
8. [Screens to Build](#8-screens-to-build)
9. [State Management](#9-state-management)
10. [Key Features Implementation](#10-key-features-implementation)
11. [Push Notifications Setup](#11-push-notifications-setup)
12. [App Permissions](#12-app-permissions)
13. [Build & Deployment](#13-build--deployment)

---

## 1. Overview

### Scope
- **Target Users:** Citizens only (Reporters)
- **Platforms:** iOS & Android
- **Backend:** Existing FastAPI backend at `http://localhost:8000/api/v1`

### Features for Mobile App
- User authentication (Email/OTP, Google OAuth)
- Hazard reporting with camera & voice
- Interactive map with hazard markers
- Real-time alerts & notifications
- Profile management
- Support tickets

### NOT Included (Web Only)
- Authority dashboard
- Analyst verification panel
- Admin controls

---

## 2. Prerequisites & Setup

### Install Flutter
```bash
# macOS
brew install flutter

# Or download from https://flutter.dev/docs/get-started/install

# Verify installation
flutter doctor
```

### Create Project
```bash
cd /Users/patu/Desktop/coastGuardians
flutter create coast_guardians_mobile
cd coast_guardians_mobile
```

### IDE Setup
- **VS Code:** Install Flutter & Dart extensions
- **Android Studio:** Install Flutter plugin

### Run App
```bash
# iOS Simulator
flutter run -d ios

# Android Emulator
flutter run -d android

# All devices
flutter devices
flutter run
```

---

## 3. Project Structure

```
coast_guardians_mobile/
├── lib/
│   ├── main.dart                 # App entry point
│   ├── config/
│   │   ├── api_config.dart       # API base URL, endpoints
│   │   ├── app_theme.dart        # Colors, fonts, styles
│   │   └── constants.dart        # App constants
│   │
│   ├── models/                   # Data models
│   │   ├── user.dart
│   │   ├── hazard_report.dart
│   │   ├── alert.dart
│   │   ├── notification.dart
│   │   ├── location.dart
│   │   └── ticket.dart
│   │
│   ├── services/                 # API & business logic
│   │   ├── api_service.dart      # HTTP client (Dio)
│   │   ├── auth_service.dart     # Authentication
│   │   ├── hazard_service.dart   # Hazard reporting
│   │   ├── alert_service.dart    # Alerts
│   │   ├── notification_service.dart
│   │   ├── location_service.dart # GPS
│   │   └── storage_service.dart  # Local storage
│   │
│   ├── providers/                # State management (Provider/Riverpod)
│   │   ├── auth_provider.dart
│   │   ├── hazard_provider.dart
│   │   ├── alert_provider.dart
│   │   └── notification_provider.dart
│   │
│   ├── screens/                  # UI screens
│   │   ├── splash_screen.dart
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   ├── signup_screen.dart
│   │   │   ├── otp_screen.dart
│   │   │   └── forgot_password_screen.dart
│   │   ├── home/
│   │   │   └── home_screen.dart
│   │   ├── map/
│   │   │   └── map_screen.dart
│   │   ├── report/
│   │   │   ├── report_hazard_screen.dart
│   │   │   ├── my_reports_screen.dart
│   │   │   └── report_detail_screen.dart
│   │   ├── alerts/
│   │   │   ├── alerts_screen.dart
│   │   │   └── alert_detail_screen.dart
│   │   ├── notifications/
│   │   │   └── notifications_screen.dart
│   │   ├── profile/
│   │   │   ├── profile_screen.dart
│   │   │   └── edit_profile_screen.dart
│   │   └── tickets/
│   │       ├── tickets_screen.dart
│   │       └── ticket_detail_screen.dart
│   │
│   ├── widgets/                  # Reusable widgets
│   │   ├── common/
│   │   │   ├── custom_button.dart
│   │   │   ├── custom_text_field.dart
│   │   │   ├── loading_widget.dart
│   │   │   └── error_widget.dart
│   │   ├── map/
│   │   │   ├── hazard_marker.dart
│   │   │   └── map_controls.dart
│   │   └── cards/
│   │       ├── hazard_card.dart
│   │       ├── alert_card.dart
│   │       └── notification_card.dart
│   │
│   └── utils/                    # Helpers
│       ├── validators.dart
│       ├── formatters.dart
│       └── helpers.dart
│
├── assets/
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── android/                      # Android config
├── ios/                          # iOS config
├── pubspec.yaml                  # Dependencies
└── README.md
```

---

## 4. Dependencies (pubspec.yaml)

```yaml
name: coast_guardians_mobile
description: CoastGuardians - Ocean Hazards Crowdsourcing App
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter

  # UI
  cupertino_icons: ^1.0.6
  google_fonts: ^6.1.0
  flutter_svg: ^2.0.9
  cached_network_image: ^3.3.1
  shimmer: ^3.0.0

  # State Management
  provider: ^6.1.1
  # OR use riverpod
  # flutter_riverpod: ^2.4.9

  # HTTP & API
  dio: ^5.4.0
  retrofit: ^4.0.3
  json_annotation: ^4.8.1

  # Authentication
  flutter_secure_storage: ^9.0.0
  google_sign_in: ^6.2.1

  # Maps
  google_maps_flutter: ^2.5.3
  # OR use flutter_map for OpenStreetMap
  # flutter_map: ^6.1.0
  # latlong2: ^0.9.0

  # Location
  geolocator: ^11.0.0
  geocoding: ^2.1.1

  # Camera & Media
  image_picker: ^1.0.7
  camera: ^0.10.5+9

  # Audio Recording
  record: ^5.0.4
  audioplayers: ^5.2.1

  # Push Notifications
  firebase_core: ^2.25.4
  firebase_messaging: ^14.7.15
  flutter_local_notifications: ^16.3.2

  # Local Storage
  shared_preferences: ^2.2.2
  hive: ^2.2.3
  hive_flutter: ^1.1.0

  # Utilities
  intl: ^0.18.1
  url_launcher: ^6.2.4
  permission_handler: ^11.3.0
  connectivity_plus: ^5.0.2

  # Loading & Refresh
  pull_to_refresh: ^2.0.0
  infinite_scroll_pagination: ^4.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.1
  build_runner: ^2.4.8
  json_serializable: ^6.7.1
  retrofit_generator: ^8.0.6
  hive_generator: ^2.0.1

flutter:
  uses-material-design: true

  assets:
    - assets/images/
    - assets/icons/

  fonts:
    - family: Poppins
      fonts:
        - asset: assets/fonts/Poppins-Regular.ttf
        - asset: assets/fonts/Poppins-Medium.ttf
          weight: 500
        - asset: assets/fonts/Poppins-Bold.ttf
          weight: 700
```

---

## 5. API Configuration

### config/api_config.dart
```dart
class ApiConfig {
  // Change this to your production URL
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // For Android emulator use: 'http://10.0.2.2:8000/api/v1'
  // For iOS simulator use: 'http://localhost:8000/api/v1'
  // For real device use your computer's IP: 'http://192.168.x.x:8000/api/v1'

  // Auth endpoints
  static const String login = '/auth/login';
  static const String signup = '/auth/signup';
  static const String verifyOtp = '/auth/verify-otp';
  static const String refreshToken = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String me = '/auth/me';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';
  static const String googleAuth = '/auth/google/callback';

  // Profile endpoints
  static const String profile = '/profile/me';
  static const String profilePicture = '/profile/picture';
  static const String fcmToken = '/profile/fcm-token';

  // Hazard endpoints
  static const String hazards = '/hazards';
  static const String myReports = '/hazards/my-reports';
  static const String mapData = '/hazards/map-data';
  static const String oceanData = '/hazards/ocean-data';

  // Alert endpoints
  static const String alerts = '/alerts';

  // Multi-hazard endpoints
  static const String multiHazardHealth = '/multi-hazard/health';
  static const String locations = '/multi-hazard/public/locations';
  static const String realTimeAlerts = '/multi-hazard/public/alerts';
  static const String cycloneData = '/multi-hazard/public/cyclone-data';

  // Notification endpoints
  static const String notifications = '/notifications';
  static const String notificationStats = '/notifications/stats';
  static const String markAllRead = '/notifications/mark-all-read';

  // Ticket endpoints
  static const String tickets = '/tickets/my';

  // Safety endpoints
  static const String safetyTips = '/safety/tips';

  // Transcription
  static const String transcription = '/transcription';
}
```

---

## 6. Data Models

### models/user.dart
```dart
class User {
  final String userId;
  final String name;
  final String email;
  final String? phone;
  final String role;
  final String? profilePicture;
  final int credibilityScore;
  final int totalReports;
  final int verifiedReports;
  final bool emailVerified;
  final bool phoneVerified;
  final DateTime createdAt;

  User({
    required this.userId,
    required this.name,
    required this.email,
    this.phone,
    required this.role,
    this.profilePicture,
    this.credibilityScore = 50,
    this.totalReports = 0,
    this.verifiedReports = 0,
    this.emailVerified = false,
    this.phoneVerified = false,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      userId: json['user_id'],
      name: json['name'],
      email: json['email'],
      phone: json['phone'],
      role: json['role'],
      profilePicture: json['profile_picture'],
      credibilityScore: json['credibility_score'] ?? 50,
      totalReports: json['total_reports'] ?? 0,
      verifiedReports: json['verified_reports'] ?? 0,
      emailVerified: json['email_verified'] ?? false,
      phoneVerified: json['phone_verified'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'user_id': userId,
      'name': name,
      'email': email,
      'phone': phone,
      'role': role,
      'profile_picture': profilePicture,
      'credibility_score': credibilityScore,
      'total_reports': totalReports,
      'verified_reports': verifiedReports,
    };
  }
}
```

### models/hazard_report.dart
```dart
class HazardReport {
  final String reportId;
  final String? userId;
  final String? userName;
  final String hazardType;
  final String category;
  final String description;
  final HazardLocation location;
  final String? imageUrl;
  final String? voiceNoteUrl;
  final String verificationStatus;
  final double? verificationScore;
  final DateTime createdAt;
  final DateTime? verifiedAt;
  final int views;
  final int likes;

  HazardReport({
    required this.reportId,
    this.userId,
    this.userName,
    required this.hazardType,
    required this.category,
    required this.description,
    required this.location,
    this.imageUrl,
    this.voiceNoteUrl,
    required this.verificationStatus,
    this.verificationScore,
    required this.createdAt,
    this.verifiedAt,
    this.views = 0,
    this.likes = 0,
  });

  factory HazardReport.fromJson(Map<String, dynamic> json) {
    return HazardReport(
      reportId: json['report_id'],
      userId: json['user_id'],
      userName: json['user_name'],
      hazardType: json['hazard_type'],
      category: json['category'],
      description: json['description'],
      location: HazardLocation.fromJson(json['location']),
      imageUrl: json['image_url'],
      voiceNoteUrl: json['voice_note_url'],
      verificationStatus: json['verification_status'],
      verificationScore: json['verification_score']?.toDouble(),
      createdAt: DateTime.parse(json['created_at']),
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'])
          : null,
      views: json['views'] ?? 0,
      likes: json['likes'] ?? 0,
    );
  }
}

class HazardLocation {
  final double latitude;
  final double longitude;
  final String? address;

  HazardLocation({
    required this.latitude,
    required this.longitude,
    this.address,
  });

  factory HazardLocation.fromJson(Map<String, dynamic> json) {
    return HazardLocation(
      latitude: json['latitude']?.toDouble() ?? 0.0,
      longitude: json['longitude']?.toDouble() ?? 0.0,
      address: json['address'],
    );
  }
}

// Hazard type constants
class HazardTypes {
  // Natural hazards
  static const String highWaves = 'high_waves';
  static const String ripCurrent = 'rip_current';
  static const String stormSurge = 'storm_surge';
  static const String coastalFlooding = 'coastal_flooding';
  static const String tsunamiWarning = 'tsunami_warning';
  static const String jellyfishBloom = 'jellyfish_bloom';
  static const String algalBloom = 'algal_bloom';
  static const String erosion = 'erosion';

  // Human-made hazards
  static const String oilSpill = 'oil_spill';
  static const String plasticPollution = 'plastic_pollution';
  static const String chemicalSpill = 'chemical_spill';
  static const String shipWreck = 'ship_wreck';
  static const String illegalFishing = 'illegal_fishing';
  static const String beachedAnimals = 'beached_animals';

  static List<String> get naturalTypes => [
    highWaves, ripCurrent, stormSurge, coastalFlooding,
    tsunamiWarning, jellyfishBloom, algalBloom, erosion,
  ];

  static List<String> get humanMadeTypes => [
    oilSpill, plasticPollution, chemicalSpill,
    shipWreck, illegalFishing, beachedAnimals,
  ];

  static String getDisplayName(String type) {
    return type.replaceAll('_', ' ').split(' ')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}
```

### models/alert.dart
```dart
class Alert {
  final String alertId;
  final String title;
  final String description;
  final String alertType;
  final String severity;
  final String status;
  final List<String> regions;
  final List<AlertCoordinate>? coordinates;
  final List<String>? recommendations;
  final DateTime issuedAt;
  final DateTime? effectiveFrom;
  final DateTime? expiresAt;
  final String? createdBy;

  Alert({
    required this.alertId,
    required this.title,
    required this.description,
    required this.alertType,
    required this.severity,
    required this.status,
    required this.regions,
    this.coordinates,
    this.recommendations,
    required this.issuedAt,
    this.effectiveFrom,
    this.expiresAt,
    this.createdBy,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      alertId: json['alert_id'],
      title: json['title'],
      description: json['description'],
      alertType: json['alert_type'],
      severity: json['severity'],
      status: json['status'],
      regions: List<String>.from(json['regions'] ?? []),
      coordinates: json['coordinates'] != null
          ? (json['coordinates'] as List)
              .map((c) => AlertCoordinate.fromJson(c))
              .toList()
          : null,
      recommendations: json['recommendations'] != null
          ? List<String>.from(json['recommendations'])
          : null,
      issuedAt: DateTime.parse(json['issued_at']),
      effectiveFrom: json['effective_from'] != null
          ? DateTime.parse(json['effective_from'])
          : null,
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'])
          : null,
      createdBy: json['created_by'],
    );
  }

  Color get severityColor {
    switch (severity) {
      case 'critical': return Colors.red;
      case 'high': return Colors.orange;
      case 'medium': return Colors.yellow;
      case 'low': return Colors.green;
      default: return Colors.blue;
    }
  }
}

class AlertCoordinate {
  final double lat;
  final double lon;

  AlertCoordinate({required this.lat, required this.lon});

  factory AlertCoordinate.fromJson(Map<String, dynamic> json) {
    return AlertCoordinate(
      lat: json['lat']?.toDouble() ?? 0.0,
      lon: json['lon']?.toDouble() ?? 0.0,
    );
  }
}
```

### models/notification.dart
```dart
class AppNotification {
  final String notificationId;
  final String type;
  final String severity;
  final String title;
  final String message;
  final bool isRead;
  final String? alertId;
  final String? reportId;
  final DateTime createdAt;

  AppNotification({
    required this.notificationId,
    required this.type,
    required this.severity,
    required this.title,
    required this.message,
    required this.isRead,
    this.alertId,
    this.reportId,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      notificationId: json['notification_id'],
      type: json['type'],
      severity: json['severity'],
      title: json['title'],
      message: json['message'],
      isRead: json['is_read'] ?? false,
      alertId: json['alert_id'],
      reportId: json['report_id'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

---

## 7. API Service Layer

### services/api_service.dart
```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/api_config.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late Dio _dio;
  final _storage = const FlutterSecureStorage();

  ApiService._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));

    // Add interceptor for auth token
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Try to refresh token
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry the request
            final retryResponse = await _retry(error.requestOptions);
            return handler.resolve(retryResponse);
          }
        }
        return handler.next(error);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await _dio.post(
        ApiConfig.refreshToken,
        data: {'refresh_token': refreshToken},
      );

      if (response.statusCode == 200) {
        await _storage.write(
          key: 'access_token',
          value: response.data['access_token'],
        );
        await _storage.write(
          key: 'refresh_token',
          value: response.data['refresh_token'],
        );
        return true;
      }
    } catch (e) {
      print('Token refresh failed: $e');
    }
    return false;
  }

  Future<Response> _retry(RequestOptions requestOptions) async {
    final token = await _storage.read(key: 'access_token');
    final options = Options(
      method: requestOptions.method,
      headers: {
        ...requestOptions.headers,
        'Authorization': 'Bearer $token',
      },
    );
    return _dio.request(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }

  // GET request
  Future<Response> get(String path, {Map<String, dynamic>? queryParams}) async {
    return await _dio.get(path, queryParameters: queryParams);
  }

  // POST request
  Future<Response> post(String path, {dynamic data}) async {
    return await _dio.post(path, data: data);
  }

  // PUT request
  Future<Response> put(String path, {dynamic data}) async {
    return await _dio.put(path, data: data);
  }

  // DELETE request
  Future<Response> delete(String path) async {
    return await _dio.delete(path);
  }

  // Multipart POST (for file uploads)
  Future<Response> postMultipart(String path, FormData formData) async {
    return await _dio.post(
      path,
      data: formData,
      options: Options(
        headers: {'Content-Type': 'multipart/form-data'},
      ),
    );
  }

  // Save tokens
  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: 'access_token', value: accessToken);
    await _storage.write(key: 'refresh_token', value: refreshToken);
  }

  // Clear tokens
  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  // Check if logged in
  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }
}
```

### services/auth_service.dart
```dart
import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/user.dart';
import 'api_service.dart';

class AuthService {
  final _api = ApiService();

  // Sign up
  Future<Map<String, dynamic>> signup({
    required String email,
    required String password,
    required String name,
    String? phone,
  }) async {
    final response = await _api.post(ApiConfig.signup, data: {
      'email': email,
      'password': password,
      'name': name,
      'phone': phone,
    });
    return response.data;
  }

  // Verify OTP
  Future<Map<String, dynamic>> verifyOtp({
    required String userId,
    required String otp,
    required String type,
  }) async {
    final response = await _api.post(ApiConfig.verifyOtp, data: {
      'user_id': userId,
      'otp': otp,
      'type': type,
    });

    if (response.data['success'] == true) {
      await _api.saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );
    }
    return response.data;
  }

  // Login
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await _api.post(ApiConfig.login, data: {
      'email': email,
      'password': password,
    });

    if (response.data['success'] == true) {
      await _api.saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );
    }
    return response.data;
  }

  // Google Sign In
  Future<Map<String, dynamic>> googleSignIn(String idToken) async {
    final response = await _api.post(ApiConfig.googleAuth, data: {
      'id_token': idToken,
    });

    if (response.data['success'] == true) {
      await _api.saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );
    }
    return response.data;
  }

  // Get current user
  Future<User> getCurrentUser() async {
    final response = await _api.get(ApiConfig.me);
    return User.fromJson(response.data);
  }

  // Logout
  Future<void> logout() async {
    try {
      await _api.post(ApiConfig.logout);
    } finally {
      await _api.clearTokens();
    }
  }

  // Forgot password
  Future<Map<String, dynamic>> forgotPassword(String email) async {
    final response = await _api.post(ApiConfig.forgotPassword, data: {
      'email': email,
    });
    return response.data;
  }

  // Reset password
  Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
  }) async {
    final response = await _api.post(ApiConfig.resetPassword, data: {
      'email': email,
      'otp': otp,
      'new_password': newPassword,
    });
    return response.data;
  }

  // Check if logged in
  Future<bool> isLoggedIn() => _api.isLoggedIn();
}
```

### services/hazard_service.dart
```dart
import 'dart:io';
import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/hazard_report.dart';
import 'api_service.dart';

class HazardService {
  final _api = ApiService();

  // Submit hazard report
  Future<Map<String, dynamic>> submitReport({
    required String hazardType,
    required String category,
    required double latitude,
    required double longitude,
    required String address,
    required String description,
    required File image,
    File? voiceNote,
  }) async {
    final formData = FormData.fromMap({
      'hazard_type': hazardType,
      'category': category,
      'latitude': latitude,
      'longitude': longitude,
      'address': address,
      'description': description,
      'image': await MultipartFile.fromFile(
        image.path,
        filename: 'hazard_image.jpg',
      ),
      if (voiceNote != null)
        'voice_note': await MultipartFile.fromFile(
          voiceNote.path,
          filename: 'voice_note.m4a',
        ),
    });

    final response = await _api.postMultipart(ApiConfig.hazards, formData);
    return response.data;
  }

  // Get my reports
  Future<Map<String, dynamic>> getMyReports({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await _api.get(
      ApiConfig.myReports,
      queryParams: {'page': page, 'page_size': pageSize},
    );
    return response.data;
  }

  // Get report details
  Future<HazardReport> getReportDetails(String reportId) async {
    final response = await _api.get('${ApiConfig.hazards}/$reportId');
    return HazardReport.fromJson(response.data);
  }

  // Get verified reports (public feed)
  Future<Map<String, dynamic>> getVerifiedReports({
    int page = 1,
    int pageSize = 20,
    String? hazardType,
    String? category,
  }) async {
    final response = await _api.get(
      ApiConfig.hazards,
      queryParams: {
        'page': page,
        'page_size': pageSize,
        'verification_status': 'verified',
        if (hazardType != null) 'hazard_type': hazardType,
        if (category != null) 'category': category,
      },
    );
    return response.data;
  }

  // Get map data
  Future<Map<String, dynamic>> getMapData({
    int hours = 24,
    bool includeHeatmap = true,
    bool includeClusters = true,
  }) async {
    final response = await _api.get(
      ApiConfig.mapData,
      queryParams: {
        'hours': hours,
        'include_heatmap': includeHeatmap,
        'include_clusters': includeClusters,
      },
    );
    return response.data;
  }

  // Get ocean data
  Future<Map<String, dynamic>> getOceanData({
    bool includeWaves = true,
    bool includeCurrents = true,
  }) async {
    final response = await _api.get(
      ApiConfig.oceanData,
      queryParams: {
        'include_waves': includeWaves,
        'include_currents': includeCurrents,
      },
    );
    return response.data;
  }

  // Like/Unlike report
  Future<Map<String, dynamic>> toggleLike(String reportId) async {
    final response = await _api.post('${ApiConfig.hazards}/$reportId/like');
    return response.data;
  }

  // Delete report
  Future<void> deleteReport(String reportId) async {
    await _api.delete('${ApiConfig.hazards}/$reportId');
  }
}
```

### services/alert_service.dart
```dart
import '../config/api_config.dart';
import '../models/alert.dart';
import 'api_service.dart';

class AlertService {
  final _api = ApiService();

  // Get active alerts
  Future<List<Alert>> getActiveAlerts() async {
    final response = await _api.get(
      ApiConfig.alerts,
      queryParams: {'status': 'active'},
    );

    final alerts = (response.data['alerts'] as List)
        .map((json) => Alert.fromJson(json))
        .toList();
    return alerts;
  }

  // Get alert details
  Future<Alert> getAlertDetails(String alertId) async {
    final response = await _api.get('${ApiConfig.alerts}/$alertId');
    return Alert.fromJson(response.data);
  }

  // Get monitored locations
  Future<Map<String, dynamic>> getMonitoredLocations() async {
    final response = await _api.get(ApiConfig.locations);
    return response.data;
  }

  // Get real-time multi-hazard alerts
  Future<Map<String, dynamic>> getRealTimeAlerts({
    int minLevel = 1,
    int limit = 100,
  }) async {
    final response = await _api.get(
      ApiConfig.realTimeAlerts,
      queryParams: {'min_level': minLevel, 'limit': limit},
    );
    return response.data;
  }

  // Get cyclone data
  Future<Map<String, dynamic>> getCycloneData({
    bool includeForecast = true,
    bool includeSurge = true,
  }) async {
    final response = await _api.get(
      ApiConfig.cycloneData,
      queryParams: {
        'include_forecast': includeForecast,
        'include_surge': includeSurge,
      },
    );
    return response.data;
  }

  // Get safety tips
  Future<Map<String, dynamic>> getSafetyTips(String hazardType) async {
    final response = await _api.get(
      ApiConfig.safetyTips,
      queryParams: {'hazard_type': hazardType},
    );
    return response.data;
  }
}
```

---

## 8. Screens to Build

### 8.1 Authentication Flow
```
SplashScreen
    ↓
[Check Token]
    ↓
LoginScreen ←→ SignupScreen
    ↓
OtpScreen
    ↓
HomeScreen
```

### 8.2 Main App Screens

| Screen | Description | API Used |
|--------|-------------|----------|
| **HomeScreen** | Dashboard with stats, recent alerts, quick actions | `/auth/me`, `/alerts`, `/notifications/stats` |
| **MapScreen** | Interactive map with hazard markers, layers | `/hazards/map-data`, `/hazards/ocean-data`, `/multi-hazard/public/locations` |
| **ReportHazardScreen** | Multi-step form: Type → Image → Location → Description | `/hazards` (POST) |
| **MyReportsScreen** | List of user's submitted reports | `/hazards/my-reports` |
| **ReportDetailScreen** | Single report details with verification status | `/hazards/{id}` |
| **AlertsScreen** | Active alerts list | `/alerts`, `/multi-hazard/public/alerts` |
| **AlertDetailScreen** | Single alert with recommendations | `/alerts/{id}` |
| **NotificationsScreen** | Push notifications list | `/notifications` |
| **ProfileScreen** | User profile with stats | `/profile/me` |
| **EditProfileScreen** | Edit profile form | `/profile/me` (PUT) |
| **TicketsScreen** | Support tickets | `/tickets/my` |
| **TicketDetailScreen** | Chat-like ticket messages | `/tickets/{id}` |

### 8.3 Screen Flow Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                      BOTTOM NAV BAR                         │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│   Home   │   Map    │  Report  │  Alerts  │    Profile     │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴───────┬────────┘
     │          │          │          │             │
     ▼          ▼          ▼          ▼             ▼
 Dashboard   MapView   ReportFlow  AlertList   ProfileView
     │          │          │          │             │
     │          │          ├─Step1    │             ├─MyReports
     │          │          ├─Step2    │             ├─Notifications
     │          │          ├─Step3    │             ├─Tickets
     │          │          └─Step4    │             └─Settings
     │          │                     │
     └──────────┴─────────────────────┴─────────────────────→ Details
```

---

## 9. State Management

### Using Provider (Recommended for beginners)

### providers/auth_provider.dart
```dart
import 'package:flutter/material.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

enum AuthStatus { initial, loading, authenticated, unauthenticated, error }

class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();

  User? _user;
  AuthStatus _status = AuthStatus.initial;
  String? _errorMessage;

  User? get user => _user;
  AuthStatus get status => _status;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  // Check authentication on app start
  Future<void> checkAuth() async {
    _status = AuthStatus.loading;
    notifyListeners();

    try {
      final isLoggedIn = await _authService.isLoggedIn();
      if (isLoggedIn) {
        _user = await _authService.getCurrentUser();
        _status = AuthStatus.authenticated;
      } else {
        _status = AuthStatus.unauthenticated;
      }
    } catch (e) {
      _status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  // Login
  Future<bool> login(String email, String password) async {
    _status = AuthStatus.loading;
    _errorMessage = null;
    notifyListeners();

    try {
      final result = await _authService.login(
        email: email,
        password: password,
      );

      if (result['success'] == true) {
        _user = User.fromJson(result['user']);
        _status = AuthStatus.authenticated;
        notifyListeners();
        return true;
      } else {
        _errorMessage = result['error']?['message'] ?? 'Login failed';
        _status = AuthStatus.error;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = e.toString();
      _status = AuthStatus.error;
      notifyListeners();
      return false;
    }
  }

  // Signup
  Future<Map<String, dynamic>> signup({
    required String email,
    required String password,
    required String name,
    String? phone,
  }) async {
    _status = AuthStatus.loading;
    notifyListeners();

    try {
      final result = await _authService.signup(
        email: email,
        password: password,
        name: name,
        phone: phone,
      );
      _status = AuthStatus.unauthenticated;
      notifyListeners();
      return result;
    } catch (e) {
      _status = AuthStatus.error;
      notifyListeners();
      rethrow;
    }
  }

  // Verify OTP
  Future<bool> verifyOtp(String userId, String otp, String type) async {
    _status = AuthStatus.loading;
    notifyListeners();

    try {
      final result = await _authService.verifyOtp(
        userId: userId,
        otp: otp,
        type: type,
      );

      if (result['success'] == true) {
        _user = User.fromJson(result['user']);
        _status = AuthStatus.authenticated;
        notifyListeners();
        return true;
      }
      _status = AuthStatus.unauthenticated;
      notifyListeners();
      return false;
    } catch (e) {
      _status = AuthStatus.error;
      notifyListeners();
      return false;
    }
  }

  // Logout
  Future<void> logout() async {
    await _authService.logout();
    _user = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
```

### main.dart with Provider setup
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/auth_provider.dart';
import 'providers/hazard_provider.dart';
import 'providers/alert_provider.dart';
import 'screens/splash_screen.dart';
import 'config/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => HazardProvider()),
        ChangeNotifierProvider(create: (_) => AlertProvider()),
      ],
      child: MaterialApp(
        title: 'CoastGuardians',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        home: const SplashScreen(),
      ),
    );
  }
}
```

---

## 10. Key Features Implementation

### 10.1 Camera & Image Picker
```dart
import 'dart:io';
import 'package:image_picker/image_picker.dart';

class ImagePickerHelper {
  static final ImagePicker _picker = ImagePicker();

  static Future<File?> pickFromCamera() async {
    final XFile? image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 80,
      maxWidth: 1920,
      maxHeight: 1080,
    );
    return image != null ? File(image.path) : null;
  }

  static Future<File?> pickFromGallery() async {
    final XFile? image = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 80,
      maxWidth: 1920,
      maxHeight: 1080,
    );
    return image != null ? File(image.path) : null;
  }
}
```

### 10.2 Voice Recording
```dart
import 'dart:io';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';

class VoiceRecorder {
  final _recorder = AudioRecorder();
  String? _recordingPath;

  Future<bool> hasPermission() async {
    return await _recorder.hasPermission();
  }

  Future<void> startRecording() async {
    if (await hasPermission()) {
      final dir = await getTemporaryDirectory();
      _recordingPath = '${dir.path}/voice_note_${DateTime.now().millisecondsSinceEpoch}.m4a';

      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path: _recordingPath!,
      );
    }
  }

  Future<File?> stopRecording() async {
    final path = await _recorder.stop();
    if (path != null) {
      return File(path);
    }
    return null;
  }

  Future<void> dispose() async {
    await _recorder.dispose();
  }
}
```

### 10.3 Location Service
```dart
import 'package:geolocator/geolocator.dart';
import 'package:geocoding/geocoding.dart';

class LocationService {
  static Future<bool> checkPermission() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return false;
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        return false;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      return false;
    }

    return true;
  }

  static Future<Position?> getCurrentPosition() async {
    if (!await checkPermission()) return null;

    return await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    );
  }

  static Future<String?> getAddressFromCoordinates(
    double latitude,
    double longitude,
  ) async {
    try {
      List<Placemark> placemarks = await placemarkFromCoordinates(
        latitude,
        longitude,
      );

      if (placemarks.isNotEmpty) {
        Placemark place = placemarks.first;
        return '${place.street}, ${place.locality}, ${place.administrativeArea}';
      }
    } catch (e) {
      print('Geocoding error: $e');
    }
    return null;
  }
}
```

### 10.4 Google Maps Integration
```dart
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class HazardMapScreen extends StatefulWidget {
  @override
  _HazardMapScreenState createState() => _HazardMapScreenState();
}

class _HazardMapScreenState extends State<HazardMapScreen> {
  GoogleMapController? _mapController;
  Set<Marker> _markers = {};

  // Default center: Indian Ocean
  static const LatLng _defaultCenter = LatLng(15.8, 80.2);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GoogleMap(
        initialCameraPosition: CameraPosition(
          target: _defaultCenter,
          zoom: 5,
        ),
        onMapCreated: (controller) {
          _mapController = controller;
          _loadHazardMarkers();
        },
        markers: _markers,
        myLocationEnabled: true,
        myLocationButtonEnabled: true,
        mapType: MapType.normal,
      ),
    );
  }

  Future<void> _loadHazardMarkers() async {
    // Fetch map data from API and add markers
    // final mapData = await hazardService.getMapData();
    // Convert to markers and update state
  }

  BitmapDescriptor _getMarkerIcon(String severity) {
    switch (severity) {
      case 'critical':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed);
      case 'high':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueOrange);
      case 'medium':
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueYellow);
      default:
        return BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueGreen);
    }
  }
}
```

---

## 11. Push Notifications Setup

### 11.1 Firebase Setup
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a new project or select existing
3. Add Android app (package name: `com.coastguardians.mobile`)
4. Add iOS app (bundle ID: `com.coastguardians.mobile`)
5. Download `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)

### 11.2 Notification Service
```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  static Future<void> initialize() async {
    await Firebase.initializeApp();

    // Request permission
    await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _localNotifications.initialize(settings);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle background messages
    FirebaseMessaging.onBackgroundMessage(_handleBackgroundMessage);
  }

  static Future<String?> getToken() async {
    return await _fcm.getToken();
  }

  static void _handleForegroundMessage(RemoteMessage message) {
    _showLocalNotification(
      title: message.notification?.title ?? 'CoastGuardians',
      body: message.notification?.body ?? '',
    );
  }

  static Future<void> _handleBackgroundMessage(RemoteMessage message) async {
    // Handle background notification
    print('Background message: ${message.messageId}');
  }

  static Future<void> _showLocalNotification({
    required String title,
    required String body,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'coast_guardians_channel',
      'CoastGuardians Alerts',
      importance: Importance.high,
      priority: Priority.high,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
    );
  }
}
```

---

## 12. App Permissions

### Android (android/app/src/main/AndroidManifest.xml)
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- Internet -->
    <uses-permission android:name="android.permission.INTERNET" />

    <!-- Location -->
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

    <!-- Camera -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature android:name="android.hardware.camera" android:required="false" />

    <!-- Microphone -->
    <uses-permission android:name="android.permission.RECORD_AUDIO" />

    <!-- Storage -->
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

    <!-- Notifications -->
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <application
        android:label="CoastGuardians"
        android:icon="@mipmap/ic_launcher">

        <!-- Google Maps API Key -->
        <meta-data
            android:name="com.google.android.geo.API_KEY"
            android:value="YOUR_GOOGLE_MAPS_API_KEY"/>

        <!-- ... rest of application config -->
    </application>
</manifest>
```

### iOS (ios/Runner/Info.plist)
```xml
<dict>
    <!-- Location -->
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>CoastGuardians needs your location to report hazards accurately</string>
    <key>NSLocationAlwaysUsageDescription</key>
    <string>CoastGuardians needs your location for hazard alerts</string>

    <!-- Camera -->
    <key>NSCameraUsageDescription</key>
    <string>CoastGuardians needs camera access to capture hazard photos</string>

    <!-- Photo Library -->
    <key>NSPhotoLibraryUsageDescription</key>
    <string>CoastGuardians needs photo access to upload hazard images</string>

    <!-- Microphone -->
    <key>NSMicrophoneUsageDescription</key>
    <string>CoastGuardians needs microphone access to record voice notes</string>
</dict>
```

---

## 13. Build & Deployment

### Android Build
```bash
# Debug APK
flutter build apk --debug

# Release APK
flutter build apk --release

# App Bundle (for Play Store)
flutter build appbundle --release

# Output: build/app/outputs/flutter-apk/app-release.apk
```

### iOS Build
```bash
# Debug
flutter build ios --debug

# Release
flutter build ios --release

# Open in Xcode for App Store submission
open ios/Runner.xcworkspace
```

### Environment Configuration
Create different configurations for dev/staging/prod:

```dart
// lib/config/environment.dart
enum Environment { dev, staging, prod }

class EnvironmentConfig {
  static Environment current = Environment.dev;

  static String get apiBaseUrl {
    switch (current) {
      case Environment.dev:
        return 'http://localhost:8000/api/v1';
      case Environment.staging:
        return 'https://staging.coastguardians.com/api/v1';
      case Environment.prod:
        return 'https://api.coastguardians.com/api/v1';
    }
  }
}
```

---

## Quick Start Checklist

### Setup
- [ ] Install Flutter SDK
- [ ] Create Flutter project
- [ ] Add dependencies to pubspec.yaml
- [ ] Run `flutter pub get`
- [ ] Set up Firebase project
- [ ] Add google-services.json (Android)
- [ ] Add GoogleService-Info.plist (iOS)
- [ ] Configure Google Maps API key

### Core Implementation
- [ ] API service layer
- [ ] Authentication flow
- [ ] State management (Provider)
- [ ] Navigation setup

### Screens
- [ ] Splash screen
- [ ] Login/Signup/OTP screens
- [ ] Home dashboard
- [ ] Map screen with markers
- [ ] Report hazard flow
- [ ] My reports list
- [ ] Alerts screen
- [ ] Notifications screen
- [ ] Profile screen

### Features
- [ ] Camera integration
- [ ] Voice recording
- [ ] GPS location
- [ ] Push notifications
- [ ] Offline support (optional)

### Testing & Deployment
- [ ] Test on Android emulator
- [ ] Test on iOS simulator
- [ ] Test on real devices
- [ ] Build release APK
- [ ] Submit to Play Store
- [ ] Submit to App Store

---

## Resources

- [Flutter Documentation](https://docs.flutter.dev)
- [Dart Language](https://dart.dev/guides)
- [Provider Package](https://pub.dev/packages/provider)
- [Dio HTTP Client](https://pub.dev/packages/dio)
- [Google Maps Flutter](https://pub.dev/packages/google_maps_flutter)
- [Firebase Flutter](https://firebase.flutter.dev)

---

**Document Version:** 1.0
**Last Updated:** December 1, 2025
**For:** CoastGuardians Mobile App (Citizen-Side)
