import { useEffect } from 'react'
import { useStore } from './store'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ArtifactPanel from './components/ArtifactPanel'
import ChatPanel from './components/ChatPanel'
import NotificationToast from './components/NotificationToast'

export default function App() {
  const loadInitial = useStore(s => s.loadInitial)

  useEffect(() => { loadInitial() }, [loadInitial])

  return (
    <div className="flex h-screen overflow-hidden bg-zepto-bg">
      <NotificationToast />
      {/* Left sidebar */}
      <Sidebar />

      {/* Center column: header + scrollable artifact area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar />
        <div className="flex-1 min-h-0 overflow-y-auto p-5">
          <ArtifactPanel />
        </div>
      </div>

      {/* Right chat panel */}
      <ChatPanel />
    </div>
  )
}
