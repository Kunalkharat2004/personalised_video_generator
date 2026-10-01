export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message, { status, cause } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.cause = cause
  }
}

const GENERIC_ERROR_MESSAGE =
  'Something went wrong while processing your selfie. Please try again.'

const GENERIC_VIDEO_ERROR_MESSAGE =
  'Something went wrong while creating your video. Please try again.'

/** Uploads the visitor's name + selfie and returns { success, visitor_name, image_id, processed_image_url }. */
export async function processSelfie(name, imageBlob) {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('file', imageBlob, 'selfie.jpg')

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/process-image`, {
      method: 'POST',
      body: formData,
    })
  } catch (err) {
    throw new ApiError(
      'Could not reach the server. Please check your connection and try again.',
      { cause: err },
    )
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    // Non-JSON body (e.g. a proxy error page) — fall through to the status check below.
  }

  if (!response.ok) {
    const detail = body?.detail
    throw new ApiError(typeof detail === 'string' ? detail : GENERIC_ERROR_MESSAGE, {
      status: response.status,
    })
  }

  return body
}

export function resolveApiUrl(path) {
  return `${API_BASE_URL}${path}`
}

/** Requests the personalized video render and returns { success, video_id, visitor_name, video_url }. */
export async function generateVideo(visitorName, imageId) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/generate-video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visitor_name: visitorName, image_id: imageId }),
    })
  } catch (err) {
    throw new ApiError(
      'Could not reach the server. Please check your connection and try again.',
      { cause: err },
    )
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    // Non-JSON body (e.g. a proxy error page) — fall through to the status check below.
  }

  if (!response.ok) {
    const detail = body?.detail
    throw new ApiError(typeof detail === 'string' ? detail : GENERIC_VIDEO_ERROR_MESSAGE, {
      status: response.status,
    })
  }

  return body
}
