import { motion } from 'framer-motion'
import {
  User, GitBranch, AlertCircle, Wand2,
  Code2, BarChart2, ChevronRight, BookOpen,
} from 'lucide-react'

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.45 } },
}
const stagger = { show: { transition: { staggerChildren: 0.1 } } }

/* ── Architecture flow diagram ────────────────────────────────────────────── */
const FLOW_STEPS = [
  { icon: <User      className="w-5 h-5" />, label: 'User Query',          color: 'bg-primary-600',   desc: 'Plain English question from the user' },
  { icon: <GitBranch className="w-5 h-5" />, label: 'Intent Router',       color: 'bg-teal-500',      desc: 'Classifies as SQL or GENERAL intent' },
  { icon: <AlertCircle className="w-5 h-5"/>, label: 'Ambiguity Checker',  color: 'bg-amber-500',     desc: 'Flags unclear or under-specified queries' },
  { icon: <Wand2     className="w-5 h-5" />, label: 'SQL Generator',       color: 'bg-violet-600',    desc: 'Translates refined query to PostgreSQL' },
  { icon: <Code2     className="w-5 h-5" />, label: 'SQL Guardrails',      color: 'bg-green-600',     desc: 'Safety validation — SELECT-only enforcement' },
  { icon: <GitBranch className="w-5 h-5" />, label: 'Supabase DB',         color: 'bg-primary-500',   desc: 'Executes SQL against live hospital database' },
  { icon: <BarChart2 className="w-5 h-5" />, label: 'Result Interpreter',  color: 'bg-teal-600',      desc: 'Picks chart type and generates AI insights' },
]

function ArchitectureDiagram() {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-6">
      <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500" />
        System Architecture
      </h2>
      <div className="flex flex-col gap-3">
        {FLOW_STEPS.map((step, i) => (
          <div key={i} className="flex items-start gap-4">
            <div className={`w-10 h-10 rounded-xl ${step.color} flex items-center justify-center text-white flex-shrink-0 shadow-sm`}>
              {step.icon}
            </div>
            <div className="flex-1 pt-1">
              <p className="font-semibold text-slate-800 dark:text-white text-sm">{step.label}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">{step.desc}</p>
            </div>
            {i < FLOW_STEPS.length - 1 && (
              <div className="absolute ml-5 mt-10 w-0.5 h-3 bg-slate-200 dark:bg-slate-600" style={{ left: 'auto' }} />
            )}
          </div>
        ))}
      </div>

      {/* Arrow flow diagram */}
      <div className="mt-8 flex flex-wrap items-center gap-1 justify-center">
        {FLOW_STEPS.map((step, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className={`px-3 py-1.5 rounded-lg text-xs font-semibold text-white ${step.color} shadow-sm`}>
              {step.label}
            </span>
            {i < FLOW_STEPS.length - 1 && (
              <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── How to use steps ─────────────────────────────────────────────────────── */
function HowToUse() {
  const steps = [
    { num: '01', title: 'Go to Dashboard',                 desc: 'Navigate to the Medicore Dashboard from the top navigation bar.' },
    { num: '02', title: 'Enter your question',             desc: 'Type a plain English question in the chat box, e.g., "Show top 5 doctors by patient count."' },
    { num: '03', title: 'View your results',               desc: 'Medicore generates SQL, queries the database, and shows charts, tables, or text insights.' },
    { num: '04', title: 'Refine if needed',                desc: 'If the query is ambiguous, a refinement modal will guide you to add more detail.' },
    { num: '05', title: 'Export charts or data',           desc: 'Use the Export PNG or Download CSV buttons to save results for reports.' },
  ]

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-6">
      <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500" />
        How to Use Medicore
      </h2>
      <div className="space-y-5">
        {steps.map((s) => (
          <div key={s.num} className="flex gap-4">
            <div className="w-9 h-9 rounded-xl bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-primary-600 dark:text-primary-400">{s.num}</span>
            </div>
            <div className="pt-1">
              <p className="font-semibold text-slate-800 dark:text-white text-sm">{s.title}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mt-0.5">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Agent descriptions ───────────────────────────────────────────────────── */
const AGENTS = [
  {
    name: 'Intent Router',
    icon: <GitBranch className="w-5 h-5 text-teal-600" />,
    bg:   'bg-teal-50 dark:bg-teal-900/20',
    desc: 'Classifies every incoming query as either "SQL" (data retrieval) or "GENERAL" (conversational). Non-SQL queries are gracefully rejected, preventing unnecessary processing.',
  },
  {
    name: 'Ambiguity Checker',
    icon: <AlertCircle className="w-5 h-5 text-amber-600" />,
    bg:   'bg-amber-50 dark:bg-amber-900/20',
    desc: 'Evaluates whether the SQL-bound query is clear enough to translate. If ambiguous, the web UI presents a refinement modal prompting the user for more specific details.',
  },
  {
    name: 'SQL Generator',
    icon: <Code2 className="w-5 h-5 text-violet-600" />,
    bg:   'bg-violet-50 dark:bg-violet-900/20',
    desc: 'Converts the natural language query into valid PostgreSQL using the hospital database schema. Selects only relevant tables to keep the context concise and accurate.',
  },
  {
    name: 'SQL Guardrails',
    icon: <Wand2 className="w-5 h-5 text-green-600" />,
    bg:   'bg-green-50 dark:bg-green-900/20',
    desc: 'A 4-stage safety pipeline: input sanity, prohibited keyword detection (DROP, DELETE, etc.), SELECT-only enforcement, and LLM-assisted syntax validation.',
  },
  {
    name: 'Result Interpreter',
    icon: <BarChart2 className="w-5 h-5 text-primary-600" />,
    bg:   'bg-primary-50 dark:bg-primary-900/20',
    desc: 'Selects the most appropriate visualisation (bar, line, pie, table, or text) based on the result shape, then generates AI-powered narrative insights using the chart context.',
  },
]

function AgentCard({ agent }) {
  return (
    <motion.div variants={fadeUp}
      className="flex gap-4 p-5 rounded-2xl bg-white dark:bg-slate-800 shadow-card border border-slate-100 dark:border-slate-700"
    >
      <div className={`w-11 h-11 rounded-xl ${agent.bg} flex items-center justify-center flex-shrink-0`}>
        {agent.icon}
      </div>
      <div>
        <h3 className="font-semibold text-slate-800 dark:text-white mb-1">{agent.name}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{agent.desc}</p>
      </div>
    </motion.div>
  )
}

/* ── Page ─────────────────────────────────────────────────────────────────── */
export default function Help() {
  return (
    <main className="min-h-screen bg-medical-bg dark:bg-slate-900 py-10">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-primary-600" /> Help & Documentation
          </h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400">Everything you need to know about Medicore.</p>
        </div>

        <ArchitectureDiagram />
        <HowToUse />

        {/* Agent descriptions */}
        <div>
          <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-5 flex items-center gap-2">
            <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500" />
            AI Agent Descriptions
          </h2>
          <motion.div
            initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
            variants={stagger}
            className="grid sm:grid-cols-2 gap-5"
          >
            {AGENTS.map((a) => <AgentCard key={a.name} agent={a} />)}
          </motion.div>
        </div>

        {/* FAQ */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-6">
          <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-5 flex items-center gap-2">
            <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500" />
            Frequently Asked Questions
          </h2>
          {[
            { q: 'Can Medicore delete or modify data?', a: 'No. All generated SQL is validated by a guardrails layer that strictly enforces SELECT-only queries. Destructive operations (DELETE, UPDATE, DROP, etc.) are blocked before reaching the database.' },
            { q: 'What database does Medicore connect to?', a: 'Medicore connects to a Supabase PostgreSQL database containing hospital management data — patients, doctors, admissions, diagnoses, billing, and more.' },
            { q: 'What happens if my query is ambiguous?', a: 'An Ambiguity Checker agent detects vague queries and the UI presents a friendly modal asking you to refine. Your clarification is then used for SQL generation.' },
            { q: 'How is cost calculated?', a: 'Token cost is estimated based on prompt and completion tokens consumed by the LLM pipeline, using standard OpenRouter / OpenAI pricing rates.' },
          ].map(({ q, a }) => (
            <details key={q} className="group border-b border-slate-100 dark:border-slate-700 last:border-0 py-4">
              <summary className="flex justify-between cursor-pointer text-sm font-semibold text-slate-700 dark:text-slate-200 list-none">
                {q}
                <ChevronRight className="w-4 h-4 text-slate-400 group-open:rotate-90 transition-transform flex-shrink-0 mt-0.5" />
              </summary>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </main>
  )
}
