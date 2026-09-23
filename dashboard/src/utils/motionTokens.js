/**
 * Motion System Design Tokens
 * Follows Auralis "Engineered Softness" motion language:
 * Intentional, restrained, cubic-bezier timing, smooth spatial depth.
 */

export const MOTION_TOKENS = {
  duration: {
    instant: '100ms',
    fast: '200ms',
    normal: '350ms',
    relaxed: '500ms',
    cinematic: '800ms',
  },
  easing: {
    // Auralis smooth exponential ease-out
    default: 'cubic-bezier(0.16, 1, 0.3, 1)',
    springy: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    subtle: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
    decel: 'cubic-bezier(0.0, 0.0, 0.2, 1)',
  },
  distance: {
    micro: '4px',
    subtle: '8px',
    medium: '16px',
    entrance: '24px',
  },
  stagger: {
    base: 60, // ms
    card: 80,
  }
};
