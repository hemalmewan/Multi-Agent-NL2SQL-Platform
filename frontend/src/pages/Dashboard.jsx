import PrebuiltCharts from '../components/dashboard/PrebuiltCharts'
import ChatInterface from '../components/dashboard/ChatInterface'

export default function Dashboard() {
  return (
    <main className="min-h-screen bg-medical-bg dark:bg-slate-900 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-14">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Medicore Dashboard
          </h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400">
            Pre-built hospital analytics and an AI-powered query interface.
          </p>
        </div>

        {/* Pre-built charts */}
        <section>
          <PrebuiltCharts />
        </section>

        {/* Chat + query */}
        <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-6">
          <ChatInterface />
        </section>
      </div>
    </main>
  )
}
