import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { useSubmitJob } from '@/hooks/useJobs'
import type { JobCreate, GPUType, JobType } from '@/types'

const GPU_TYPES: GPUType[] = ['any', 'T4-16GB', 'A10G-24GB', 'V100-16GB', 'V100-32GB', 'A100-40GB', 'A100-80GB']
const JOB_TYPES: { value: JobType; label: string }[] = [
  { value: 'training', label: 'Training' },
  { value: 'fine_tuning', label: 'Fine-tuning' },
  { value: 'inference', label: 'Inference' },
  { value: 'batch', label: 'Batch' },
]
const REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1', 'us-central1', 'us-east1', 'europe-west4', 'eastus', 'westus2', 'westeurope']

interface FormValues {
  name: string
  model: string
  job_type: JobType
  priority: number
  gpu_type: GPUType
  gpu_count: number
  gpu_memory_gb: string
  preferred_regions: string[]
  budget: string
  sla_deadline: string
  use_spot: boolean
  estimated_duration_hours: string
}

export function JobSubmissionForm() {
  const navigate = useNavigate()
  const submitJob = useSubmitJob()

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      job_type: 'training',
      priority: 5,
      gpu_type: 'any',
      gpu_count: 1,
      use_spot: true,
    },
  })

  const onSubmit = async (values: FormValues) => {
    const payload: JobCreate = {
      name: values.name,
      model: values.model || undefined,
      job_type: values.job_type,
      priority: Number(values.priority),
      gpu_type: values.gpu_type === 'any' ? undefined : values.gpu_type,
      gpu_count: Number(values.gpu_count),
      gpu_memory_gb: values.gpu_memory_gb ? Number(values.gpu_memory_gb) : undefined,
      preferred_regions: values.preferred_regions?.length ? values.preferred_regions : undefined,
      budget: values.budget ? Number(values.budget) : undefined,
      sla_deadline: values.sla_deadline || undefined,
      use_spot: values.use_spot,
      estimated_duration_hours: values.estimated_duration_hours
        ? Number(values.estimated_duration_hours)
        : undefined,
    }

    const job = await submitJob.mutateAsync(payload)
    navigate(`/jobs/${job.id}`)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
      {/* Basic Info */}
      <section className="bg-surface-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4">Job Details</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs text-slate-400 mb-1">Job Name *</label>
            <input
              {...register('name', { required: 'Name is required' })}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
              placeholder="e.g. LLaMA-3 Fine-tune"
            />
            {errors.name && <p className="text-rose-400 text-xs mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Model</label>
            <input
              {...register('model')}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
              placeholder="e.g. llama-3-8b"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Job Type</label>
            <select
              {...register('job_type')}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            >
              {JOB_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* GPU Requirements */}
      <section className="bg-surface-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4">GPU Requirements</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">GPU Type</label>
            <select
              {...register('gpu_type')}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            >
              {GPU_TYPES.map((t) => (
                <option key={t} value={t}>{t === 'any' ? 'Any GPU' : t}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">GPU Count</label>
            <input
              {...register('gpu_count', { required: true, min: 1, max: 64 })}
              type="number"
              min={1}
              max={64}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Min GPU Memory (GB)</label>
            <input
              {...register('gpu_memory_gb')}
              type="number"
              min={1}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
              placeholder="Optional"
            />
          </div>
        </div>
      </section>

      {/* Scheduling */}
      <section className="bg-surface-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4">Scheduling &amp; Cost</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Priority (1–10)</label>
            <input
              {...register('priority', { min: 1, max: 10 })}
              type="number"
              min={1}
              max={10}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Budget (USD)</label>
            <input
              {...register('budget')}
              type="number"
              min={0}
              step={0.01}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
              placeholder="Optional max spend"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Est. Duration (hours)</label>
            <input
              {...register('estimated_duration_hours')}
              type="number"
              min={0}
              step={0.1}
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
              placeholder="Optional"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">SLA Deadline</label>
            <input
              {...register('sla_deadline')}
              type="datetime-local"
              className="w-full bg-surface-700 rounded-lg px-3 py-2 text-white text-sm border border-surface-600 focus:outline-none focus:border-primary-500"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                {...register('use_spot')}
                type="checkbox"
                className="w-4 h-4 rounded accent-primary-500"
              />
              <span className="text-sm text-slate-300">
                Use spot/preemptible instances{' '}
                <span className="text-emerald-400 text-xs">(~70% cheaper, may be interrupted)</span>
              </span>
            </label>
          </div>
        </div>
      </section>

      {/* Region Preferences */}
      <section className="bg-surface-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-2">Preferred Regions</h2>
        <p className="text-slate-500 text-xs mb-3">Select regions to prefer (leave empty for any)</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {REGIONS.map((r) => (
            <label key={r} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                value={r}
                {...register('preferred_regions')}
                className="w-3.5 h-3.5 rounded accent-primary-500"
              />
              <span className="text-xs text-slate-300">{r}</span>
            </label>
          ))}
        </div>
      </section>

      {/* Submit */}
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submitJob.isPending}
          className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg text-sm transition-colors disabled:opacity-60"
        >
          {submitJob.isPending ? 'Submitting…' : 'Submit Job'}
        </button>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="px-6 py-2.5 bg-surface-700 hover:bg-surface-600 text-slate-300 font-medium rounded-lg text-sm transition-colors"
        >
          Cancel
        </button>
      </div>

      {submitJob.isError && (
        <p className="text-rose-400 text-sm">
          Failed to submit job. Please check your input and try again.
        </p>
      )}
    </form>
  )
}
