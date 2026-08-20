import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface RaceBackgroundProps {
  className?: string
}

/**
 * The hero's "wow": a stylized 3D circuit loop, slowly rotating, with a
 * warm point of light chasing it (a car) over a faintly undulating
 * telemetry grid — plain three.js (not @react-three/fiber): this is one
 * isolated, imperative WebGL scene with its own render loop that has to
 * be paused/resumed outside of React's render cycle (tab visibility,
 * on/off screen, prefers-reduced-motion) — a raw useEffect + canvas ref
 * keeps that lifecycle explicit and easy to audit, without pulling in a
 * whole React-reconciler-for-WebGL dependency (and its React 19
 * compatibility surface) for a single background component.
 *
 * Deliberately used ONLY on the landing hero (see RaceSelectionPage) —
 * every other screen uses the static CSS `.ambient-backdrop` instead
 * (see index.css), per the brief: dramatic where it's the protagonist,
 * absent (not just dimmed) where it would compete with dense data.
 *
 * POSITIONING: this component just fills whatever box it's given — it
 * doesn't know it's on the right half of the hero. Keeping the circuit
 * out of the text column is done by the CALLER constraining this
 * component's container to the right portion of the hero (see
 * RaceSelectionPage), not by offsetting the 3D scene's own coordinates —
 * simpler, and the camera math here stays reusable if the layout changes.
 *
 * PERFORMANCE: capped devicePixelRatio, paused via
 * document.visibilitychange (tab hidden) and IntersectionObserver
 * (scrolled out of view), and prefers-reduced-motion skips WebGL
 * entirely in favor of one static frame — never left spinning where
 * nobody can see it.
 */
export function RaceBackground({ className }: RaceBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    let prefersReducedMotion = reducedMotionQuery.matches

    const accentColor = new THREE.Color(
      getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() ||
        '#ff2d3f',
    )

    const scene = new THREE.Scene()
    // Slightly tighter FOV + a bit further back than the first pass — this
    // component now renders inside a narrower (right-half-of-hero, not
    // full-width) container, so the framing needs to stay comfortable at a
    // taller/narrower aspect ratio too.
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100)
    const basePosition = new THREE.Vector3(0, 3.3, 8.6)
    camera.position.copy(basePosition)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)

    const trackGroup = new THREE.Group()
    scene.add(trackGroup)

    // A closed, stylized circuit loop (not a real track — just enough
    // shape variation to read as one at a glance).
    const controlPoints = [
      new THREE.Vector3(0, 0, 3.2),
      new THREE.Vector3(1.8, 0.15, 3.6),
      new THREE.Vector3(3.4, 0.3, 2.6),
      new THREE.Vector3(3.9, 0.1, 0.8),
      new THREE.Vector3(3.0, -0.1, -0.6),
      new THREE.Vector3(3.6, 0.2, -2.2),
      new THREE.Vector3(2.2, 0.35, -3.4),
      new THREE.Vector3(0.2, 0.1, -3.0),
      new THREE.Vector3(-1.4, -0.15, -3.6),
      new THREE.Vector3(-3.2, 0.05, -2.4),
      new THREE.Vector3(-3.6, 0.25, -0.4),
      new THREE.Vector3(-2.4, 0.1, 1.2),
      new THREE.Vector3(-2.8, -0.2, 2.6),
      new THREE.Vector3(-1.2, 0.1, 3.4),
    ]
    const curve = new THREE.CatmullRomCurve3(controlPoints, true, 'catmullrom', 0.5)

    const trackGeometry = new THREE.TubeGeometry(curve, 220, 0.035, 8, true)
    const trackMaterial = new THREE.MeshBasicMaterial({
      color: accentColor,
      transparent: true,
      opacity: 0.85,
    })
    trackGroup.add(new THREE.Mesh(trackGeometry, trackMaterial))

    // A wider, additively-blended tube behind it fakes a glow/halo
    // without a full postprocessing bloom pass.
    const haloGeometry = new THREE.TubeGeometry(curve, 220, 0.11, 8, true)
    const haloMaterial = new THREE.MeshBasicMaterial({
      color: accentColor,
      transparent: true,
      opacity: 0.16,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    trackGroup.add(new THREE.Mesh(haloGeometry, haloMaterial))

    // The "car": a warm point of light chasing the loop.
    const car = new THREE.Mesh(
      new THREE.SphereGeometry(0.065, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xfff1dc }),
    )
    const carGlow = new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 16, 16),
      new THREE.MeshBasicMaterial({
        color: 0xffb066,
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    )
    const carLight = new THREE.PointLight(0xffb066, 3.2, 5, 2)
    trackGroup.add(car, carGlow, carLight)

    // A faint telemetry grid drifting beneath the track.
    const gridGeometry = new THREE.PlaneGeometry(16, 16, 36, 36)
    gridGeometry.rotateX(-Math.PI / 2)
    gridGeometry.translate(0, -1.3, 0)
    const gridMaterial = new THREE.MeshBasicMaterial({
      color: accentColor,
      wireframe: true,
      transparent: true,
      opacity: 0.05,
    })
    const grid = new THREE.Mesh(gridGeometry, gridMaterial)
    trackGroup.add(grid)
    const gridBasePositions = Float32Array.from(gridGeometry.attributes.position.array)

    function resize() {
      const { clientWidth, clientHeight } = container!
      if (clientWidth === 0 || clientHeight === 0) return
      camera.aspect = clientWidth / clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(clientWidth, clientHeight)
    }
    resize()

    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container)

    // Subtle mouse parallax — clamped so it never feels like a full
    // camera drag, just the scene "noticing" the pointer.
    const targetParallax = { x: 0, y: 0 }
    const parallax = { x: 0, y: 0 }
    function handlePointerMove(event: PointerEvent) {
      const rect = container!.getBoundingClientRect()
      const nx = ((event.clientX - rect.left) / rect.width) * 2 - 1
      const ny = ((event.clientY - rect.top) / rect.height) * 2 - 1
      targetParallax.x = THREE.MathUtils.clamp(nx, -1, 1) * 0.6
      targetParallax.y = THREE.MathUtils.clamp(ny, -1, 1) * -0.3
    }
    window.addEventListener('pointermove', handlePointerMove)

    const clock = new THREE.Clock()
    let carProgress = 0
    let frameId: number | null = null

    function renderFrame() {
      const delta = Math.min(clock.getDelta(), 0.1)
      const elapsed = clock.getElapsedTime()

      trackGroup.rotation.y += delta * 0.06

      parallax.x += (targetParallax.x - parallax.x) * 0.05
      parallax.y += (targetParallax.y - parallax.y) * 0.05
      camera.position.set(basePosition.x + parallax.x, basePosition.y + parallax.y, basePosition.z)
      camera.lookAt(0, 0, 0)

      carProgress = (carProgress + delta * 0.07) % 1
      const point = curve.getPointAt(carProgress)
      car.position.copy(point)
      carGlow.position.copy(point)
      carLight.position.copy(point)

      const positions = gridGeometry.attributes.position
      for (let i = 0; i < positions.count; i++) {
        const baseX = gridBasePositions[i * 3]
        const baseZ = gridBasePositions[i * 3 + 2]
        const baseY = gridBasePositions[i * 3 + 1]
        positions.setY(i, baseY + Math.sin(baseX * 0.5 + elapsed * 0.6) * 0.06 + Math.cos(baseZ * 0.5 + elapsed * 0.4) * 0.06)
      }
      positions.needsUpdate = true

      renderer.render(scene, camera)
    }

    function loop() {
      renderFrame()
      frameId = requestAnimationFrame(loop)
    }

    function startLoop() {
      if (frameId !== null || prefersReducedMotion) return
      clock.start()
      frameId = requestAnimationFrame(loop)
    }

    function stopLoop() {
      if (frameId !== null) {
        cancelAnimationFrame(frameId)
        frameId = null
      }
    }

    if (prefersReducedMotion) {
      // One static frame, camera at rest — the shape is still visible,
      // it just never animates.
      renderFrame()
    } else {
      // Start immediately — don't wait for the IntersectionObserver's
      // first callback to be what kicks the loop off. (That callback DOES
      // fire on observe() in practice, but a hero that's supposed to be
      // animated from the first frame shouldn't depend on it; the
      // observer below is wired purely to PAUSE/resume afterwards.)
      startLoop()
    }

    let isIntersecting = true

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible' && isIntersecting && !prefersReducedMotion) {
        startLoop()
      } else {
        stopLoop()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)

    const intersectionObserver = new IntersectionObserver(
      ([entry]) => {
        isIntersecting = entry.isIntersecting
        if (isIntersecting && document.visibilityState === 'visible' && !prefersReducedMotion) {
          startLoop()
        } else {
          stopLoop()
        }
      },
      { threshold: 0.05 },
    )
    intersectionObserver.observe(container)

    // Not just checked once at mount: if the preference changes live (e.g.
    // toggled in DevTools' Rendering panel while testing, or the OS setting
    // flipped) the scene reacts immediately instead of needing a reload —
    // still strictly binary either way, never a "half-dead" in-between.
    function handleReducedMotionChange(event: MediaQueryListEvent) {
      prefersReducedMotion = event.matches
      if (prefersReducedMotion) {
        stopLoop()
        renderFrame()
      } else if (isIntersecting && document.visibilityState === 'visible') {
        startLoop()
      }
    }
    reducedMotionQuery.addEventListener('change', handleReducedMotionChange)

    return () => {
      stopLoop()
      reducedMotionQuery.removeEventListener('change', handleReducedMotionChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('pointermove', handlePointerMove)
      resizeObserver.disconnect()
      intersectionObserver.disconnect()
      container.removeChild(renderer.domElement)

      trackGeometry.dispose()
      haloGeometry.dispose()
      gridGeometry.dispose()
      car.geometry.dispose()
      carGlow.geometry.dispose()
      trackMaterial.dispose()
      haloMaterial.dispose()
      gridMaterial.dispose()
      ;(car.material as THREE.Material).dispose()
      ;(carGlow.material as THREE.Material).dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      aria-hidden="true"
      style={{ pointerEvents: 'none' }}
    />
  )
}
