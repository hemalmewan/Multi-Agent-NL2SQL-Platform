export default function LoadingSpinner({ size = 'md', label = 'Processing…' }) {
  const sz = size === 'sm' ? 'w-5 h-5' : size === 'lg' ? 'w-12 h-12' : 'w-8 h-8'
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className={`${sz} border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin`} />
      {label && (
        <p className="text-sm text-slate-500 dark:text-slate-400 animate-pulse">{label}</p>
      )}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-5 shadow-card animate-pulse">
      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-3" />
      <div className="h-48 bg-slate-100 dark:bg-slate-700 rounded-lg" />
    </div>
  )
}
