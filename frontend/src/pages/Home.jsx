import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity, BarChart3, Brain, Database, ArrowRight,
  MessageSquare, Zap, Shield, Github, Linkedin,
  Stethoscope, Users, HeartPulse, TrendingUp,
} from 'lucide-react'

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.55, ease: 'easeOut' } },
}
const stagger = { show: { transition: { staggerChildren: 0.12 } } }

/* ── Section: Hero ────────────────────────────────────────────────────────── */
function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-50 via-white to-teal-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 pt-20 pb-28">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(37,99,235,0.08),transparent)] pointer-events-none" />
      <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
        <motion.div
          initial="hidden" animate="show" variants={stagger}
          className="flex flex-col items-center gap-6"
        >
          <motion.div variants={fadeUp}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-sm font-medium border border-primary-200 dark:border-primary-800"
          >
            <Zap className="w-3.5 h-3.5" /> AI-Powered Medical Analytics
          </motion.div>

          <motion.h1 variants={fadeUp}
            className="text-5xl sm:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight tracking-tight"
          >
            Medicore:{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-teal-500">
              Ask Anything,
            </span>
            <br />Understand Everything.
          </motion.h1>

          <motion.p variants={fadeUp}
            className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed"
          >
            Type a question in plain English — like{' '}
            <em>"Show monthly revenue trends"</em> — and Medicore instantly translates it
            into SQL, queries your hospital database, and renders interactive charts.
            No SQL knowledge required.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-wrap justify-center gap-4 mt-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold text-base shadow-lg shadow-primary-200 dark:shadow-primary-900/30 transition-all hover:-translate-y-0.5"
            >
              Go to Dashboard <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/help"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-base hover:border-primary-300 dark:hover:border-primary-600 transition-all"
            >
              How it works
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

/* ── Section: Product overview ────────────────────────────────────────────── */
function ProductOverview() {
  const steps = [
    { icon: <MessageSquare className="w-6 h-6 text-primary-600" />, title: 'Ask in Plain English', desc: 'Type your question naturally — no SQL, no coding required. Medicore understands medical context.' },
    { icon: <Brain className="w-6 h-6 text-teal-600" />,           title: 'AI Translates to SQL',  desc: 'A multi-agent pipeline validates, refines, and converts your query into precise PostgreSQL.' },
    { icon: <Database className="w-6 h-6 text-primary-600" />,     title: 'Live Database Query',   desc: 'Your hospital database is queried in real-time — results are always fresh and accurate.' },
    { icon: <BarChart3 className="w-6 h-6 text-teal-600" />,       title: 'Instant Visualisation', desc: 'Results appear as interactive charts, tables, or AI-generated text insights automatically.' },
  ]

  return (
    <section className="py-24 bg-white dark:bg-slate-900">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div
          initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}
          variants={stagger}
          className="text-center mb-14"
        >
          <motion.h2 variants={fadeUp} className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-4">
            From Question to Insight in Seconds
          </motion.h2>
          <motion.p variants={fadeUp} className="text-slate-500 dark:text-slate-400 text-lg max-w-xl mx-auto">
            Designed for doctors, hospital administrators, and health data analysts — zero technical background needed.
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}
          variants={stagger}
          className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {steps.map((s, i) => (
            <motion.div key={i} variants={fadeUp}
              className="relative bg-slate-50 dark:bg-slate-800 rounded-2xl p-6 border border-slate-100 dark:border-slate-700 hover:shadow-card-hover transition-shadow"
            >
              <div className="w-12 h-12 rounded-xl bg-white dark:bg-slate-700 shadow-card flex items-center justify-center mb-4">
                {s.icon}
              </div>
              <span className="absolute top-4 right-4 text-3xl font-extrabold text-slate-100 dark:text-slate-700 select-none">
                {String(i + 1).padStart(2, '0')}
              </span>
              <h3 className="font-semibold text-slate-800 dark:text-white mb-2">{s.title}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

/* ── Section: Who benefits ────────────────────────────────────────────────── */
function AudienceSection() {
  const roles = [
    { icon: <Stethoscope className="w-8 h-8" />, label: 'Doctors',         color: 'text-primary-600 bg-primary-50 dark:bg-primary-900/30' },
    { icon: <HeartPulse   className="w-8 h-8" />, label: 'Nurses',          color: 'text-teal-600 bg-teal-50 dark:bg-teal-900/30' },
    { icon: <Users        className="w-8 h-8" />, label: 'Administrators',  color: 'text-violet-600 bg-violet-50 dark:bg-violet-900/30' },
    { icon: <TrendingUp   className="w-8 h-8" />, label: 'Data Analysts',   color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30' },
  ]

  return (
    <section className="py-20 bg-gradient-to-b from-slate-50 to-white dark:from-slate-800 dark:to-slate-900">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }} variants={stagger}>
          <motion.h2 variants={fadeUp} className="text-3xl font-bold text-slate-900 dark:text-white mb-3">
            Built for Healthcare Professionals
          </motion.h2>
          <motion.p variants={fadeUp} className="text-slate-500 dark:text-slate-400 mb-12">
            Medicore empowers every member of your hospital team — no training required.
          </motion.p>
          <motion.div variants={stagger} className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {roles.map((r, i) => (
              <motion.div key={i} variants={fadeUp}
                className={`rounded-2xl p-6 flex flex-col items-center gap-3 ${r.color}`}
              >
                {r.icon}
                <span className="font-semibold text-slate-800 dark:text-white">{r.label}</span>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

/* ── Section: Features ────────────────────────────────────────────────────── */
function Features() {
  const features = [
    { icon: <MessageSquare className="w-5 h-5 text-primary-600" />, title: 'Natural Language Queries', desc: 'Ask questions exactly how you think — no SQL syntax, no keywords.' },
    { icon: <BarChart3     className="w-5 h-5 text-teal-600" />,    title: 'Auto Chart Generation',   desc: 'Bar, line, and pie charts are selected and rendered automatically.' },
    { icon: <Zap           className="w-5 h-5 text-amber-500" />,   title: 'Real-time Insights',      desc: 'AI-generated narrative summaries explain what the data means.' },
    { icon: <Shield        className="w-5 h-5 text-green-600" />,   title: 'SQL Guardrails',           desc: 'Multi-stage safety checks ensure only safe SELECT queries run.' },
    { icon: <Activity      className="w-5 h-5 text-violet-600" />,  title: 'Usage Tracking',           desc: 'Monitor token usage, cost, and latency on the Settings page.' },
    { icon: <Database      className="w-5 h-5 text-primary-600" />, title: 'Supabase Integration',    desc: 'Connects directly to your hospital Supabase PostgreSQL database.' },
  ]

  return (
    <section className="py-24 bg-white dark:bg-slate-900">
      <div className="max-w-6xl mx-auto px-6">
        <motion.div initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }} variants={stagger}>
          <motion.div variants={fadeUp} className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-4">
              Everything You Need to Explore Your Data
            </h2>
          </motion.div>
          <motion.div variants={stagger} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <motion.div key={i} variants={fadeUp}
                className="flex gap-4 p-6 rounded-2xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 hover:shadow-card-hover transition-shadow"
              >
                <div className="w-10 h-10 flex-shrink-0 rounded-xl bg-white dark:bg-slate-700 shadow-card flex items-center justify-center">
                  {f.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800 dark:text-white mb-1">{f.title}</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{f.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

/* ── Section: Developer ───────────────────────────────────────────────────── */
function DeveloperInfo() {
  return (
    <section className="py-24 bg-gradient-to-br from-primary-600 to-teal-500">
      <div className="max-w-3xl mx-auto px-6">
        <motion.div
          initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.4 }}
          variants={stagger}
          className="bg-white/10 backdrop-blur-sm rounded-3xl p-10 flex flex-col sm:flex-row gap-8 items-center text-white"
        >
          {/* Avatar */}
          <motion.div variants={fadeUp} className="flex-shrink-0">
            <img
              src="/images/user_profile.jpeg"
              alt="Hemal Mewantha"
              className="w-28 h-28 rounded-full border-4 border-white/50 shadow-xl object-cover"
            />
          </motion.div>

          <motion.div variants={stagger} className="flex flex-col gap-3">
            <motion.h3 variants={fadeUp} className="text-2xl font-bold">Hemal Mewantha</motion.h3>
            <motion.p variants={fadeUp} className="text-white/80 text-sm">
              Final Year Data Science Undergraduate — University of Colombo
            </motion.p>
            <motion.p variants={fadeUp} className="text-white/70 text-sm leading-relaxed">
              Passionate about AI, LLMs, and building tools that make data accessible to everyone.
              Medicore is built as part of the AI Engineering Bootcamp mini-project series.
            </motion.p>
            <motion.div variants={fadeUp} className="flex gap-3 mt-1">
              <a
                href="https://github.com/hemalmewan"
                target="_blank" rel="noreferrer"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-white text-sm font-medium transition-colors"
              >
                <Github className="w-4 h-4" /> GitHub
              </a>
              <a
                href="https://www.linkedin.com/in/hemal-mewantha"
                target="_blank" rel="noreferrer"
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/20 hover:bg-white/30 text-white text-sm font-medium transition-colors"
              >
                <Linkedin className="w-4 h-4" /> LinkedIn
              </a>
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

/* ── Page ─────────────────────────────────────────────────────────────────── */
export default function Home() {
  return (
    <main>
      <Hero />
      <ProductOverview />
      <AudienceSection />
      <Features />
      <DeveloperInfo />
    </main>
  )
}
