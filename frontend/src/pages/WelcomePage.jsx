import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import BrandHeader from '../components/BrandHeader'
import Button from '../components/Button'
import PageContainer from '../components/PageContainer'

export const VISITOR_NAME_KEY = 'visitorName'

export default function WelcomePage() {
  const [name, setName] = useState('')
  const navigate = useNavigate()

  const trimmedName = useMemo(() => name.trim(), [name])
  const isValid = trimmedName.length > 0

  const handleContinue = () => {
    if (!isValid) return
    sessionStorage.setItem(VISITOR_NAME_KEY, trimmedName)
    navigate('/selfie')
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') handleContinue()
  }

  return (
    <PageContainer>
      <BrandHeader />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.1, ease: 'easeOut' }}
        className="w-full rounded-3xl border border-white/10 bg-white/[0.04] p-10 text-center shadow-2xl backdrop-blur-xl sm:p-14"
      >
        <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl md:text-6xl">
          Create Your Townhall Video
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-white/60 sm:text-xl">
          Let&apos;s make a personalized video just for you.
        </p>

        <div className="mx-auto mt-10 flex max-w-xl flex-col items-stretch gap-5">
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your name"
            autoFocus
            className="w-full rounded-2xl border border-white/15 bg-white/5 px-6 py-5 text-center text-xl font-medium text-white placeholder:text-white/35 outline-none transition-colors focus:border-sky-400/70 focus:bg-white/10"
          />

          <Button
            onClick={handleContinue}
            disabled={!isValid}
            className="w-full"
          >
            Continue
            <ArrowRight className="h-5 w-5" />
          </Button>
        </div>
      </motion.div>
    </PageContainer>
  )
}
