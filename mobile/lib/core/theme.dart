import 'package:flutter/cupertino.dart';

import 'models.dart';

/// Light, soft palette from the design brief; iOS (Cupertino) widgets and the system font.
abstract final class AppColors {
  static const background = Color(0xFFF7F9FC);
  static const card = Color(0xFFFFFFFF);
  static const primary = Color(0xFF2563EB);
  static const primarySoft = Color(0xFFE0EAFF);
  static const text = Color(0xFF0F172A);
  static const textSecondary = Color(
    0xFF475569,
  ); // AA on white and on the background
  static const separator = Color(0xFFE2E8F0);
  static const protectionOff = Color(0xFF94A3B8);
}

const appTheme = CupertinoThemeData(
  brightness: Brightness.light,
  primaryColor: AppColors.primary,
  scaffoldBackgroundColor: AppColors.background,
  // Opaque bars skip the backdrop blur Cupertino applies to translucent ones (cheaper to draw).
  barBackgroundColor: AppColors.background,
  textTheme: CupertinoTextThemeData(
    primaryColor: AppColors.primary,
    textStyle: TextStyle(
      inherit: false,
      fontFamily: 'CupertinoSystemText',
      fontSize: 17,
      height: 1.3,
      letterSpacing: -0.41,
      color: AppColors.text,
      decoration: TextDecoration.none,
    ),
  ),
);

abstract final class AppText {
  static const title = TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: AppColors.text,
  );
  static const headline = TextStyle(
    fontSize: 19,
    fontWeight: FontWeight.w600,
    color: AppColors.text,
  );
  static const body = TextStyle(fontSize: 17, color: AppColors.text);
  static const secondary = TextStyle(
    fontSize: 16,
    color: AppColors.textSecondary,
  );
  static const sectionHeader = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w700,
    color: AppColors.text,
  );
}

/// Status is always shown as color + icon + text, never by color alone.
class RiskStyle {
  const RiskStyle({
    required this.accent,
    required this.background,
    required this.foreground,
    required this.icon,
  });

  final Color accent;
  final Color background;
  final Color foreground; // AA contrast on [background]
  final IconData icon;

  static RiskStyle of(RiskLevel level) => switch (level) {
    RiskLevel.high => const RiskStyle(
      accent: Color(0xFFDC2626),
      background: Color(0xFFFEE2E2),
      foreground: Color(0xFF991B1B),
      icon: CupertinoIcons.exclamationmark_octagon_fill,
    ),
    RiskLevel.medium => const RiskStyle(
      accent: Color(0xFFF59E0B),
      background: Color(0xFFFEF3C7),
      foreground: Color(0xFF92400E),
      icon: CupertinoIcons.exclamationmark_triangle_fill,
    ),
    RiskLevel.low => const RiskStyle(
      accent: Color(0xFF16A34A),
      background: Color(0xFFDCFCE7),
      foreground: Color(0xFF166534),
      icon: CupertinoIcons.checkmark_shield_fill,
    ),
    RiskLevel.unknown => const RiskStyle(
      accent: Color(0xFF94A3B8),
      background: Color(0xFFF1F5F9),
      foreground: Color(0xFF334155),
      icon: CupertinoIcons.question_circle_fill,
    ),
  };
}
