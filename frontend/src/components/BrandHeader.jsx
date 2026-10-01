import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'

/**
 * Generic event/department branding mark. Swap the icon/wordmark for an
 * official asset once one is added to the project — no logo is bundled here.
 */
export default function BrandHeader({ eventName = 'Townhall Experience' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mb-10 flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-2.5 backdrop-blur-sm"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-indigo-500">
        <Sparkles className="h-4 w-4 text-white" strokeWidth={2.5} />
      </span>
      <span className="text-sm font-semibold uppercase tracking-[0.2em] text-white/70">
        {eventName}
      </span>
    </motion.div>
  )
}
