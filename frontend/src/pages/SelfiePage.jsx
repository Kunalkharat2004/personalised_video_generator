import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  ArrowRight,
  Camera,
  CheckCircle2,
  Circle,
  Download,
  Loader2,
  PartyPopper,
  RotateCcw,
  Upload,
  VideoOff,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ApiError, generateVideo, processSelfie, resolveApiUrl } from '../api/client'
import BrandHeader from '../components/BrandHeader'
import Button from '../components/Button'
import PageContainer from '../components/PageContainer'
import { VISITOR_NAME_KEY } from './WelcomePage'

// Camera lifecycle: 'requesting' -> 'live' | 'denied' | 'unsupported'
const CAMERA_STATE = {
  REQUESTING: 'requesting',
  LIVE: 'live',
  DENIED: 'denied',
  UNSUPPORTED: 'unsupported',
}

// Page flow after a selfie is captured:
// 'capture' -> 'processing' -> 'ready' -> 'video_processing' -> 'video_ready' | 'error'
const STAGE = {
  CAPTURE: 'capture',
  PROCESSING: 'processing',
  READY: 'ready',
  VIDEO_PROCESSING: 'video_processing',
  VIDEO_READY: 'video_ready',
  ERROR: 'error',
}

const GENERIC_ERROR_MESSAGE =
  'Something went wrong while processing your selfie. Please try again.'
const GENERIC_VIDEO_ERROR_MESSAGE =
  'Something went wrong while creating your video. Please try again.'

// Purely cosmetic progress illusion: quick at first, crawls near the end so the
// bar never looks "finished" before the real API response actually arrives.
function nextProgressStep(current) {
  if (current < 20) return current + 3 + Math.random() * 2
  if (current < 63) return current + 1.5 + Math.random() * 1.5
  if (current < 99) return current + 0.2 + Math.random() * 0.4
  return current
}

function progressLabel(progress) {
  if (progress < 20) return 'Uploading your selfie…'
  if (progress < 63) return 'Removing the background…'
  if (progress < 99) return 'Adding the finishing touches…'
  return 'Almost done…'
}

export default function SelfiePage() {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const fileInputRef = useRef(null)
  const requestIdRef = useRef(0)

  const [visitorName, setVisitorName] = useState('')
  const [cameraState, setCameraState] = useState(CAMERA_STATE.REQUESTING)
  const [selfie, setSelfie] = useState(null) // { url, blob }
  const [captureError, setCaptureError] = useState(null)
  const [stage, setStage] = useState(STAGE.CAPTURE)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null) // { visitorName, imageUrl, imageId }
  const [processError, setProcessError] = useState(null)
  const [errorContext, setErrorContext] = useState('image') // 'image' | 'video' — decides the error retry action
  const [videoStep, setVideoStep] = useState(0) // 0 = adding name, 1 = rendering video (cosmetic only)
  const [videoResult, setVideoResult] = useState(null) // { visitorName, videoUrl }

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const startCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraState(CAMERA_STATE.UNSUPPORTED)
      return
    }

    // Guards against duplicate concurrent requests (e.g. React StrictMode's
    // dev-only double effect invocation) leaving an orphaned camera stream.
    const requestId = ++requestIdRef.current
    setCameraState(CAMERA_STATE.REQUESTING)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: 1280, height: 720 },
        audio: false,
      })
      if (requestId !== requestIdRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      setCameraState(CAMERA_STATE.LIVE)
    } catch {
      if (requestId !== requestIdRef.current) return
      setCameraState(CAMERA_STATE.DENIED)
    }
  }, [])

  // AnimatePresence (mode="wait") can mount the <video> element a bit after
  // cameraState flips to 'live', so poll a couple of frames until the node
  // and stream are both ready instead of attaching in a single effect pass.
  useEffect(() => {
    if (cameraState !== CAMERA_STATE.LIVE) return undefined

    let frameId
    let cancelled = false
    const attach = () => {
      if (cancelled) return
      if (videoRef.current && streamRef.current) {
        videoRef.current.srcObject = streamRef.current
        videoRef.current.play?.().catch(() => {})
      } else {
        frameId = requestAnimationFrame(attach)
      }
    }
    attach()

    return () => {
      cancelled = true
      if (frameId) cancelAnimationFrame(frameId)
    }
  }, [cameraState])

  useEffect(() => {
    const storedName = sessionStorage.getItem(VISITOR_NAME_KEY)
    if (!storedName) {
      navigate('/', { replace: true })
      return
    }
    setVisitorName(storedName)
    startCamera()

    return () => stopStream()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleTakeSelfie = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !video.videoWidth) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCaptureError('Could not capture the photo. Please try again.')
          return
        }
        setCaptureError(null)
        const url = URL.createObjectURL(blob)
        setSelfie({ url, blob })
        stopStream()
      },
      'image/jpeg',
      0.92,
    )
  }

  const handleRetake = () => {
    if (selfie) URL.revokeObjectURL(selfie.url)
    setSelfie(null)
    setStage(STAGE.CAPTURE)
    setResult(null)
    setVideoResult(null)
    setProcessError(null)
    setCaptureError(null)
    startCamera()
  }

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    stopStream()
    const url = URL.createObjectURL(file)
    setSelfie({ url, blob: file })
    event.target.value = ''
  }

  const handleContinue = async () => {
    if (!selfie) {
      setProcessError('No selfie was found. Please take or upload one first.')
      setErrorContext('image')
      setStage(STAGE.ERROR)
      return
    }

    setStage(STAGE.PROCESSING)
    setProgress(0)
    setProcessError(null)

    try {
      const data = await processSelfie(visitorName, selfie.blob)
      setProgress(100)
      // let the bar visibly reach 100% before switching views
      await new Promise((resolve) => setTimeout(resolve, 300))
      setResult({
        visitorName: data.visitor_name,
        imageUrl: resolveApiUrl(data.processed_image_url),
        imageId: data.image_id,
      })
      setStage(STAGE.READY)
    } catch (err) {
      console.error('Selfie processing failed:', err)
      setProcessError(err instanceof ApiError ? err.message : GENERIC_ERROR_MESSAGE)
      setErrorContext('image')
      setStage(STAGE.ERROR)
    }
  }

  const handleGenerateVideo = async () => {
    if (!result) return

    setStage(STAGE.VIDEO_PROCESSING)
    setVideoStep(0)
    setProcessError(null)
    // Purely cosmetic pacing so the checklist doesn't jump straight to "rendering"
    // before the (usually longer) ffmpeg render has actually started.
    const stepTimer = setTimeout(() => setVideoStep(1), 1800)

    try {
      const data = await generateVideo(result.visitorName, result.imageId)
      setVideoResult({
        visitorName: data.visitor_name,
        videoUrl: resolveApiUrl(data.video_url),
      })
      setStage(STAGE.VIDEO_READY)
    } catch (err) {
      console.error('Video generation failed:', err)
      setProcessError(err instanceof ApiError ? err.message : GENERIC_VIDEO_ERROR_MESSAGE)
      setErrorContext('video')
      setStage(STAGE.ERROR)
    } finally {
      clearTimeout(stepTimer)
    }
  }

  const handleDownload = async () => {
    if (!videoResult) return
    try {
      const response = await fetch(videoResult.videoUrl)
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = 'personalized_townhall_video.mp4'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(blobUrl)
    } catch (err) {
      console.error('Video download failed:', err)
    }
  }

  // Cosmetic progress ticker — see nextProgressStep(); never reflects real backend progress.
  useEffect(() => {
    if (stage !== STAGE.PROCESSING) return undefined
    const id = setInterval(() => {
      setProgress((current) => Math.min(99, nextProgressStep(current)))
    }, 120)
    return () => clearInterval(id)
  }, [stage])

  useEffect(() => {
    return () => {
      if (selfie) URL.revokeObjectURL(selfie.url)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const showCameraFeed = !selfie && cameraState === CAMERA_STATE.LIVE
  const showCameraError =
    !selfie &&
    (cameraState === CAMERA_STATE.DENIED ||
      cameraState === CAMERA_STATE.UNSUPPORTED)

  return (
    <PageContainer>
      <BrandHeader />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.1, ease: 'easeOut' }}
        className="w-full rounded-3xl border border-white/10 bg-white/[0.04] p-8 text-center shadow-2xl backdrop-blur-xl sm:p-12"
      >
        <AnimatePresence mode="wait">
          {stage === STAGE.READY && result ? (
            <motion.div
              key="ready"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col items-center gap-6 py-6"
            >
              <CheckCircle2 className="h-16 w-16 text-emerald-400" />
              <div>
                <h1 className="text-3xl font-bold text-white sm:text-4xl">
                  Your image is ready!
                </h1>
                <p className="mt-3 text-lg text-white/60">
                  Welcome, {result.visitorName}!
                </p>
              </div>
              <div className="rounded-2xl bg-[repeating-conic-gradient(#2a2a2a_0%_25%,#1a1a1a_0%_50%)] bg-[length:20px_20px] p-2 shadow-xl">
                <img
                  src={result.imageUrl}
                  alt={`Processed selfie for ${result.visitorName}`}
                  className="h-64 w-64 rounded-xl object-contain"
                />
              </div>
              <div className="flex flex-col gap-4 sm:flex-row">
                <Button variant="secondary" onClick={handleRetake}>
                  <RotateCcw className="h-5 w-5" />
                  Retake Selfie
                </Button>
                <Button onClick={handleGenerateVideo}>
                  Create My Video
                  <ArrowRight className="h-5 w-5" />
                </Button>
              </div>
            </motion.div>
          ) : stage === STAGE.PROCESSING ? (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col items-center gap-6 py-10"
            >
              <Loader2 className="h-14 w-14 animate-spin text-sky-400" />
              <div>
                <h1 className="text-2xl font-bold text-white sm:text-3xl">
                  Creating your personalized preview…
                </h1>
                <p className="mt-2 text-white/60">{progressLabel(progress)}</p>
              </div>
              <div className="w-full max-w-sm">
                <div className="h-3 w-full overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-sky-400 to-indigo-400"
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.15, ease: 'linear' }}
                  />
                </div>
                <p className="mt-2 text-sm font-medium text-white/50">
                  {Math.round(progress)}%
                </p>
              </div>
            </motion.div>
          ) : stage === STAGE.VIDEO_PROCESSING ? (
            <motion.div
              key="video-processing"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col items-center gap-6 py-10"
            >
              <Loader2 className="h-14 w-14 animate-spin text-sky-400" />
              <div>
                <h1 className="text-2xl font-bold text-white sm:text-3xl">
                  Creating your personalized video…
                </h1>
                <p className="mt-2 text-white/60">Please wait…</p>
              </div>
              <ul className="flex w-full max-w-xs flex-col gap-3 text-left">
                {[
                  { label: 'Selfie processed', done: true },
                  { label: 'Background removed', done: true },
                  { label: 'Photo prepared', done: true },
                  { label: 'Adding your name', done: videoStep > 0 },
                  { label: 'Rendering video', done: false },
                ].map((item, index) => (
                  <motion.li
                    key={item.label}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.08 }}
                    className="flex items-center gap-3 text-white/80"
                  >
                    {item.done ? (
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                    ) : (
                      <Circle className="h-5 w-5 shrink-0 animate-pulse text-sky-400" />
                    )}
                    {item.label}
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          ) : stage === STAGE.VIDEO_READY && videoResult ? (
            <motion.div
              key="video-ready"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col items-center gap-6 py-6"
            >
              <PartyPopper className="h-16 w-16 text-emerald-400" />
              <div>
                <h1 className="text-3xl font-bold text-white sm:text-4xl">
                  Your personalized video is ready!
                </h1>
                <p className="mt-3 text-lg text-white/60">
                  Welcome, {videoResult.visitorName}!
                </p>
              </div>
              <video
                key={videoResult.videoUrl}
                src={videoResult.videoUrl}
                controls
                playsInline
                preload="metadata"
                className="w-full max-w-xl rounded-2xl border border-white/15 bg-black shadow-xl"
              />
              <div className="flex flex-col gap-4 sm:flex-row">
                <Button variant="secondary" onClick={handleRetake}>
                  <RotateCcw className="h-5 w-5" />
                  Start Over
                </Button>
                <Button onClick={handleDownload}>
                  <Download className="h-5 w-5" />
                  Download Video
                </Button>
              </div>
            </motion.div>
          ) : stage === STAGE.ERROR ? (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col items-center gap-6 py-6"
            >
              <AlertTriangle className="h-14 w-14 text-amber-400" />
              <div>
                <h1 className="text-2xl font-bold text-white sm:text-3xl">
                  We hit a snag
                </h1>
                <p className="mt-3 max-w-sm text-white/60">
                  {processError || GENERIC_ERROR_MESSAGE}
                </p>
              </div>
              <div className="flex flex-col gap-4 sm:flex-row">
                <Button variant="secondary" onClick={handleRetake}>
                  <RotateCcw className="h-5 w-5" />
                  Retake Selfie
                </Button>
                <Button onClick={errorContext === 'video' ? handleGenerateVideo : handleContinue}>
                  Try Again
                  <ArrowRight className="h-5 w-5" />
                </Button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="capture"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Take Your Selfie
              </h1>
              <p className="mt-3 text-lg text-white/60">
                Hi {visitorName}, smile for the camera!
              </p>

              <div className="mx-auto mt-8 aspect-video w-full max-w-xl overflow-hidden rounded-2xl border border-white/15 bg-black/40 shadow-xl">
                <AnimatePresence mode="wait">
                  {selfie ? (
                    <motion.img
                      key="preview"
                      src={selfie.url}
                      alt="Captured selfie preview"
                      initial={{ opacity: 0, scale: 1.03 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.4, ease: 'easeOut' }}
                      className="h-full w-full object-cover"
                    />
                  ) : showCameraFeed ? (
                    <motion.video
                      key="live"
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.4 }}
                      className="h-full w-full -scale-x-100 object-cover"
                    />
                  ) : (
                    <motion.div
                      key="status"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex h-full w-full flex-col items-center justify-center gap-3 px-6 text-center"
                    >
                      {showCameraError ? (
                        <>
                          <VideoOff className="h-10 w-10 text-white/40" />
                          <p className="text-white/70">
                            Camera access is required to take your selfie.
                          </p>
                        </>
                      ) : (
                        <p className="text-white/50">
                          Requesting camera access…
                        </p>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <canvas ref={canvasRef} className="hidden" />

              <div className="mx-auto mt-8 flex max-w-xl flex-col items-stretch gap-4">
                {selfie ? (
                  <div className="flex flex-col gap-4 sm:flex-row">
                    <Button
                      variant="secondary"
                      onClick={handleRetake}
                      className="flex-1"
                    >
                      <RotateCcw className="h-5 w-5" />
                      Retake
                    </Button>
                    <Button onClick={handleContinue} className="flex-1">
                      Continue
                      <ArrowRight className="h-5 w-5" />
                    </Button>
                  </div>
                ) : showCameraFeed ? (
                  <Button onClick={handleTakeSelfie}>
                    <Camera className="h-5 w-5" />
                    Take Selfie
                  </Button>
                ) : null}

                {captureError && (
                  <p className="text-sm font-medium text-rose-300">
                    {captureError}
                  </p>
                )}

                {!selfie && (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="mx-auto flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white/50 transition-colors hover:text-white/80"
                  >
                    <Upload className="h-4 w-4" />
                    Upload a photo instead
                  </button>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  capture="user"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </PageContainer>
  )
}
