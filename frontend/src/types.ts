export interface ToolEvent {
  type: 'search' | 'email' | 'inbox' | 'write_staged' | string
  detail: string
  result_preview?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  roleLabel?: string
  toolEvents?: ToolEvent[]
}

export interface TaoStep {
  id: string
  node: string
  label: string
  detail: string
  color: string
  icon: string
}

export interface PendingWrite {
  tool: 'propose_update_section' | 'propose_create_file' | 'propose_delete_file'
  args: Record<string, string>
}

export interface Artifacts {
  roadmap?: string
  key_focus_areas?: string
  requirements?: string
  success_metrics?: string
  impact_quadrant?: string
  rice_score?: string
  [key: string]: string | undefined
}

export const ROLE_CONFIG: Record<string, { color: string; icon: string; access: string }> = {
  'Product Manager':          { color: '#5E17EB', icon: '👤', access: 'Full access' },
  'Finance':                  { color: '#10B981', icon: '💰', access: 'Full access' },
  'Leadership':               { color: '#F59E0B', icon: '🏆', access: 'Full access' },
  'Tech / Engineering':       { color: '#0EA5E9', icon: '⚙️',  access: 'Internal access' },
  'Design':                   { color: '#EC4899', icon: '🎨', access: 'Internal access' },
  'Growth & Marketing':       { color: '#F97316', icon: '📈', access: 'Internal access' },
  'Customer Experience (CS)': { color: '#14B8A6', icon: '🎧', access: 'Internal access' },
  'Data Science / Analytics': { color: '#8B5CF6', icon: '📊', access: 'Internal access' },
  'Operations':               { color: '#6B7280', icon: '🏭', access: 'Internal access' },
  'Other':                    { color: '#9CA3AF', icon: '👥', access: 'Public only' },
}

export const ROLES = Object.keys(ROLE_CONFIG)

export const ARTIFACT_KEYS = [
  'roadmap',
  'key_focus_areas',
  'requirements',
  'success_metrics',
  'impact_quadrant',
  'rice_score',
] as const

export type ArtifactKey = typeof ARTIFACT_KEYS[number]

export const ARTIFACT_LABELS: Record<ArtifactKey, string> = {
  roadmap:          'Roadmap',
  key_focus_areas:  'Key Focus Areas',
  requirements:     'Requirements',
  success_metrics:  'Success Metrics',
  impact_quadrant:  'Impact Quadrant',
  rice_score:       'RICE Score',
}
