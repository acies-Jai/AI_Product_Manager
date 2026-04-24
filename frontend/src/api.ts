const BASE = '/api'

export async function fetchFiles() {
  const res = await fetch(`${BASE}/files`)
  if (!res.ok) throw new Error('Failed to fetch files')
  return res.json() as Promise<{ files: string[]; indexed: boolean; chunks: number }>
}

export async function fetchArtifacts() {
  const res = await fetch(`${BASE}/artifacts`)
  if (!res.ok) throw new Error('Failed to fetch artifacts')
  return res.json() as Promise<Record<string, string>>
}

export async function indexDocuments() {
  const res = await fetch(`${BASE}/index`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to index documents')
  return res.json() as Promise<{ chunks: number; files: string[] }>
}

export async function generateArtifacts() {
  const res = await fetch(`${BASE}/generate-artifacts?notify=false`, { method: 'POST' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text)
  }
  return res.json()
}

export interface Department { key: string; label: string; emails: string[] }

export async function fetchTeam(): Promise<{ departments: Department[]; all_recipients: string[] }> {
  const res = await fetch(`${BASE}/team`)
  if (!res.ok) throw new Error('Failed to fetch team')
  return res.json()
}

export async function notifyTeam(recipients: string[] = []) {
  const res = await fetch(`${BASE}/notify-team`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recipients }),
  })
  if (!res.ok) throw new Error('Failed to notify team')
  return res.json() as Promise<{ email_status: string }>
}

export async function confirmWrite(threadId: string, confirmed: boolean) {
  const res = await fetch(`${BASE}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, confirmed }),
  })
  if (!res.ok) throw new Error('Failed to confirm write')
  return res.json() as Promise<{ reply: string }>
}

export async function* streamChat(message: string, role: string, threadId: string) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, role, thread_id: threadId }),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`)
  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch {
          // skip malformed chunk
        }
      }
    }
  }
}
