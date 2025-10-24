"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { Slider } from "@/components/ui/slider"

interface WeightSelectorProps {
  onWeightsChange?: (weights: { quality: number; costEfficiency: number; timeEfficiency: number }) => void
  initialWeights?: { quality: number; costEfficiency: number; timeEfficiency: number }
  disabled?: boolean
}

export function ScoreWeightsSelector({ onWeightsChange, initialWeights, disabled = false }: WeightSelectorProps) {
  const hasMountedRef = useRef(false)
  const [weights, setWeights] = useState({
    quality: 0.5,
    costEfficiency: 0.25,
    timeEfficiency: 0.25,
  })

  // Allow parent to provide/override initial values
  useEffect(() => {
    if (initialWeights) {
      setWeights(initialWeights)
    }
  }, [initialWeights])

  const updateWeights = useCallback(
    (key: keyof typeof weights, newValue: number) => {
      if (disabled) return;
      const clampedValue = Math.max(0, Math.min(1, newValue))

      setWeights((prevWeights) => {
        const remainingWeight = 1 - clampedValue

        let compensatingKey: keyof typeof weights
        if (key === "quality") {
          compensatingKey = "costEfficiency"
        } else if (key === "costEfficiency") {
          compensatingKey = "timeEfficiency"
        } else {
          compensatingKey = "quality"
        }

        const newWeights = { ...prevWeights, [key]: clampedValue }

        const otherKey = Object.keys(prevWeights).find(
          (k) => k !== key && k !== compensatingKey,
        ) as keyof typeof weights

        newWeights[compensatingKey] = remainingWeight - prevWeights[otherKey]

        if (newWeights[compensatingKey] < 0) {
          newWeights[compensatingKey] = 0
          newWeights[otherKey] = remainingWeight
        }

        const finalWeights = {
          quality: Math.round(newWeights.quality * 1000) / 1000,
          costEfficiency: Math.round(newWeights.costEfficiency * 1000) / 1000,
          timeEfficiency: Math.round(newWeights.timeEfficiency * 1000) / 1000,
        }

        if (!disabled && hasMountedRef.current) {
          onWeightsChange?.(finalWeights)
        }
        return finalWeights
      })
    },
    [onWeightsChange, disabled],
  )

  const formatPercentage = (value: number) => `${Math.round(value * 100)}%`

  // Only sync local state when values actually changed
  useEffect(() => {
    if (!initialWeights) return
    const changed =
      Math.abs(initialWeights.quality - weights.quality) > 1e-6 ||
      Math.abs(initialWeights.costEfficiency - weights.costEfficiency) > 1e-6 ||
      Math.abs(initialWeights.timeEfficiency - weights.timeEfficiency) > 1e-6
    if (changed) {
      setWeights(initialWeights)
    }
  }, [initialWeights, weights.quality, weights.costEfficiency, weights.timeEfficiency])

  // Mark mounted to avoid parent updates during initial render
  useEffect(() => {
    hasMountedRef.current = true
  }, [])

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">Quality</span>
          <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            {formatPercentage(weights.quality)}
          </span>
        </div>
        <Slider
          value={[weights.quality]}
          onValueChange={([value]) => updateWeights("quality", value)}
          max={1}
          min={0}
          step={0.01}
          className="w-full"
          disabled={disabled}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">Cost Efficiency</span>
          <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            {formatPercentage(weights.costEfficiency)}
          </span>
        </div>
        <Slider
          value={[weights.costEfficiency]}
          onValueChange={([value]) => updateWeights("costEfficiency", value)}
          max={1}
          min={0}
          step={0.01}
          className="w-full"
          disabled={disabled}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">Time Efficiency</span>
          <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
            {formatPercentage(weights.timeEfficiency)}
          </span>
        </div>
        <Slider
          value={[weights.timeEfficiency]}
          onValueChange={([value]) => updateWeights("timeEfficiency", value)}
          max={1}
          min={0}
          step={0.01}
          className="w-full"
          disabled={disabled}
        />
      </div>
    </div>
  )
}
