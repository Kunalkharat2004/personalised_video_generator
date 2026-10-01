import { motion } from 'framer-motion'

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
}

/**
 * Full-screen booth backdrop shared by every page: dark gradient + soft glow accents.
 */
export default function PageContainer({ children, className = '' }) {
  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-[#05070d] px-6 py-10">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-sky-500/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-[-14rem] right-[-10rem] h-[32rem] w-[32rem] rounded-full bg-indigo-500/10 blur-3xl" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] bg-[size:32px_32px]" />

      <motion.main
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.45, ease: 'easeOut' }}
        className={`relative z-10 flex w-full max-w-3xl flex-col items-center ${className}`}
      >
        {children}
      </motion.main>
    </div>
  )
}
