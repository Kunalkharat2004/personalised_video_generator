import { motion } from 'framer-motion'

const VARIANT_CLASSES = {
  primary:
    'bg-white text-slate-950 shadow-[0_8px_30px_rgba(255,255,255,0.15)] disabled:bg-white/20 disabled:text-white/40 disabled:shadow-none',
  secondary:
    'bg-white/5 text-white border border-white/15 hover:bg-white/10 disabled:opacity-40',
  danger:
    'bg-transparent text-white/70 border border-white/15 hover:bg-white/5 disabled:opacity-40',
}

/**
 * Large, touch-friendly button with subtle Framer Motion press/hover feedback.
 */
export default function Button({
  children,
  variant = 'primary',
  className = '',
  disabled = false,
  type = 'button',
  ...props
}) {
  return (
    <motion.button
      type={type}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className={`inline-flex items-center justify-center gap-3 rounded-2xl px-8 py-5 text-lg font-semibold tracking-tight transition-colors duration-200 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  )
}
