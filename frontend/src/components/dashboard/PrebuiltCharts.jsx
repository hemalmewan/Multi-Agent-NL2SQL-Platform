import { motion } from 'framer-motion'

const CHARTS = [
  {
    title: 'Revenue Trends',
    description: 'Monthly hospital revenue for the current year. Steady growth indicates effective billing and patient volume management.',
    image: '/images/Revenue_trend_each_day.png',
  },
  {
    title: 'Doctor Workload',
    description: 'Patient count per doctor over the past 30 days. Helps administration identify capacity constraints and redistribution needs.',
    image: '/images/doctors_workload.png',
  },
  {
    title: 'Top Diagnoses',
    description: 'Most frequent diagnoses in the last quarter. Guides resource allocation for specialists and medical supplies.',
    image: '/images/top_10_diagnoses.png',
  },
  {
    title: 'Payment Methods',
    description: 'Revenue distribution by payment method. Insurance dominates, but digital payments are growing rapidly.',
    image: '/images/Payment_methods.png',
  },
]

function ChartCard({ chart, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.45 }}
      className="bg-white dark:bg-slate-800 rounded-2xl shadow-card hover:shadow-card-hover transition-shadow p-5 flex flex-col"
    >
      <h3 className="text-base font-semibold text-slate-800 dark:text-white mb-1">{chart.title}</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">{chart.description}</p>
      <div className="flex-1 flex items-center justify-center overflow-hidden rounded-xl bg-slate-50 dark:bg-slate-900">
        <img
          src={chart.image}
          alt={chart.title}
          className="w-full h-auto object-contain max-h-72"
        />
      </div>
    </motion.div>
  )
}

export default function PrebuiltCharts() {
  return (
    <div>
      <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500 inline-block" />
        Hospital Analytics Overview
      </h2>
      <div className="grid md:grid-cols-2 gap-6">
        {CHARTS.map((chart, i) => (
          <ChartCard key={i} chart={chart} index={i} />
        ))}
      </div>
    </div>
  )
}
