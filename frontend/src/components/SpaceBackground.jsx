import { useEffect, useRef } from 'react'

const STAR_COUNT = 400

export default function SpaceBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    let width, height
    let stars = []
    let animationId

    function resize() {
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }

    function initStars() {
      stars = Array.from({ length: STAR_COUNT }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        z: Math.random() * width,
        speed: Math.random() * 0.5 + 0.2,
        brightness: Math.random() * 0.5 + 0.5,
      }))
    }

    function draw() {
      ctx.fillStyle = 'black'
      ctx.fillRect(0, 0, width, height)

      ctx.fillStyle = 'white'
      stars.forEach((star) => {
        star.z -= star.speed
        if (star.z <= 0) {
          star.z = width
          star.x = Math.random() * width
          star.y = Math.random() * height
        }

        const k = width / star.z
        const x = (star.x - width / 2) * k + width / 2
        const y = (star.y - height / 2) * k + height / 2
        const size = (1 - star.z / width) * 2

        ctx.globalAlpha = star.brightness
        ctx.beginPath()
        ctx.arc(x, y, size, 0, Math.PI * 2)
        ctx.fill()
      })

      ctx.globalAlpha = 1
      animationId = requestAnimationFrame(draw)
    }

    resize()
    initStars()
    draw()

    window.addEventListener('resize', resize)

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animationId)
    }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 z-0" />
}
