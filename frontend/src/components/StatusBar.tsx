import { Loader2 } from 'lucide-react'
import { useStore } from '../store'
import { ARTIFACT_KEYS } from '../types'

export default function StatusBar() {
  const { chunksIndexed, files, artifacts, staleArtifacts, isGenerating, generateArtifacts } = useStore()
  const artifactCount = ARTIFACT_KEYS.filter(k => artifacts[k]).length
  const allReady = artifactCount === 6

  return (
    <div className="card px-5 py-3 flex flex-wrap items-center gap-6 text-xs">
      <span className="text-gray-500">
        🗄️ <strong className="text-zepto-dark">{chunksIndexed}</strong> sources indexed
      </span>
      <span className="text-gray-500">
        📄 <strong className="text-zepto-dark">{files.length}</strong> knowledge files
      </span>
      <span className="text-gray-500">
        📊 <strong className="text-zepto-dark">{artifactCount}/6</strong> artefacts ready
      </span>

      {staleArtifacts ? (
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-amber-600 font-semibold">⚠ Input data changed</span>
          <button
            onClick={() => generateArtifacts()}
            disabled={isGenerating}
            className="flex items-center gap-1 bg-amber-50 border border-amber-200 text-amber-700
                       rounded-lg px-2.5 py-1 font-semibold hover:bg-amber-100 transition-colors
                       disabled:opacity-50"
          >
            {isGenerating
              ? <><Loader2 size={11} className="animate-spin" /> Regenerating…</>
              : <>↻ Regenerate</>
            }
          </button>
        </div>
      ) : (
        <span className={`font-semibold ml-auto ${allReady ? 'text-emerald-500' : 'text-amber-500'}`}>
          {allReady ? '⚡ All insights delivered' : '○ Awaiting dispatch'}
        </span>
      )}
    </div>
  )
}
