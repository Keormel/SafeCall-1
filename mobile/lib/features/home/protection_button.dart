import 'package:flutter/cupertino.dart';

import '../../core/theme.dart';
import '../../core/ui.dart';

/// Large round protection toggle. A soft ring pulses while protection is on.
class ProtectionButton extends StatefulWidget {
  const ProtectionButton({
    super.key,
    required this.enabled,
    required this.onTap,
  });

  final bool enabled;
  final VoidCallback onTap;

  @override
  State<ProtectionButton> createState() => _ProtectionButtonState();
}

class _ProtectionButtonState extends State<ProtectionButton>
    with SingleTickerProviderStateMixin {
  late final _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2000),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncAnimation();
  }

  @override
  void didUpdateWidget(ProtectionButton old) {
    super.didUpdateWidget(old);
    _syncAnimation();
  }

  void _syncAnimation() {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    if (widget.enabled && !reduceMotion) {
      if (!_pulse.isAnimating) _pulse.repeat();
    } else {
      _pulse
        ..stop()
        ..value = 0;
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final color = widget.enabled ? AppColors.primary : AppColors.protectionOff;
    const size = 176.0;

    return Semantics(
      button: true,
      toggled: widget.enabled,
      label: widget.enabled ? l.protectionOn : l.protectionOff,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Column(
          children: [
            SizedBox(
              width: size * 1.35,
              height: size * 1.35,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Isolate the 60 fps ring so the shadowed button and the page are not repainted.
                  RepaintBoundary(
                    child: AnimatedBuilder(
                      animation: _pulse,
                      builder: (_, _) {
                        final t = Curves.easeOut.transform(_pulse.value);
                        return Opacity(
                          opacity: widget.enabled ? (1 - t) * 0.35 : 0,
                          child: Container(
                            width: size * (1 + 0.35 * t),
                            height: size * (1 + 0.35 * t),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: color,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 280),
                    curve: Curves.easeOut,
                    width: size,
                    height: size,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: widget.enabled
                            ? const [Color(0xFF3B82F6), Color(0xFF1D4ED8)]
                            : const [Color(0xFFCBD5E1), Color(0xFF94A3B8)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: color.withValues(alpha: 0.35),
                          blurRadius: 28,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Icon(
                      widget.enabled
                          ? CupertinoIcons.checkmark_shield_fill
                          : CupertinoIcons.shield,
                      size: 76,
                      color: CupertinoColors.white,
                    ),
                  ),
                ],
              ),
            ),
            Text(
              widget.enabled ? l.protectionOn : l.protectionOff,
              style: AppText.title,
            ),
            const SizedBox(height: 4),
            Text(
              widget.enabled ? l.protectionOnHint : l.protectionOffHint,
              textAlign: TextAlign.center,
              style: AppText.secondary,
            ),
          ],
        ),
      ),
    );
  }
}
