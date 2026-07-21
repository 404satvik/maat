// Simulated transport for the async views. In this preview there is no live
// Python backend in the browser, so "analyzing" resolves the committed
// fixture after a short delay to exercise real loading and error states. The
// data returned is genuine pipeline output; only the round trip is simulated.
import { scenarioById } from '../data/fixtures'

export function runAnalysis(scenarioId, { delay = 850 } = {}) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const scenario = scenarioById[scenarioId]
      if (!scenario) {
        reject(new Error(`No pipeline output found for "${scenarioId}".`))
        return
      }
      resolve(scenario)
    }, delay)
  })
}
