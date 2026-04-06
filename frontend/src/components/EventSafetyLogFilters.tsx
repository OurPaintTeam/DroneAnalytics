import {useId, useState, type CSSProperties} from "react"

import {RED} from "../config"
import {LOG_SERVICE_TYPES, LOG_SEVERITIES} from "../logConstants"
import {buildEventSafetySearchParams, type EventSafetyFilterForm} from "../logQuery"
import MUIRangePicker from "./DateRangePicker"

type Props = {
    onApply: (params: URLSearchParams) => void
}

const fieldClass =
    "w-full rounded-md border border-[#d8dce6] bg-[#fbfcff] px-2.5 py-1.5 text-sm text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] transition placeholder:text-slate-400 hover:border-[#bfc5d5] hover:shadow-[0_0_0_3px_rgba(159,45,32,0.06)] focus:border-[#9F2D20] focus:bg-white focus:outline-none focus:ring-2 focus:ring-offset-0"

const emptyForm = (): EventSafetyFilterForm => ({
    from: null,
    to: null,
    service: "",
    serviceIdRaw: "",
    severity: "",
})

export default function EventSafetyLogFilters({onApply}: Props) {
    const baseId = useId()
    const [form, setForm] = useState<EventSafetyFilterForm>(emptyForm)
    const [error, setError] = useState<string | null>(null)

    const apply = () => {
        const {params, error: err} = buildEventSafetySearchParams(form)
        if (err) {
            setError(err)
            return
        }
        setError(null)
        onApply(params)
    }

    const reset = () => {
        setForm(emptyForm())
        setError(null)
        onApply(new URLSearchParams())
    }

    const ringFocus = {["--tw-ring-color" as string]: RED} as CSSProperties

    return (
        <div className="space-y-1.5">
            <div className="grid gap-2.5 md:grid-cols-12 md:items-end md:gap-x-3">
                <div className="md:col-span-4">
                    <label className="mb-1 block text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">Период</label>
                    <MUIRangePicker
                        variant="inline"
                        from={form.from}
                        to={form.to}
                        onChange={(from, to) => setForm(f => ({...f, from, to}))}
                    />
                </div>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 md:col-span-6">
                    <label className="flex flex-col gap-1">
                        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">Сервис</span>
                        <select
                            id={`${baseId}-svc`}
                            className={fieldClass}
                            style={ringFocus}
                            value={form.service}
                            onChange={e => setForm(f => ({...f, service: e.target.value}))}
                        >
                            <option value="">Все</option>
                            {LOG_SERVICE_TYPES.map(s => (
                                <option key={s} value={s}>
                                    {s}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="flex flex-col gap-1">
                        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">ID сервиса</span>
                        <input
                            id={`${baseId}-sid`}
                            type="text"
                            inputMode="numeric"
                            autoComplete="off"
                            placeholder="1–1000"
                            className={fieldClass}
                            style={ringFocus}
                            value={form.serviceIdRaw}
                            onChange={e => setForm(f => ({...f, serviceIdRaw: e.target.value}))}
                        />
                    </label>
                    <label className="flex flex-col gap-1">
                        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">Важность</span>
                        <select
                            id={`${baseId}-sev`}
                            className={fieldClass}
                            style={ringFocus}
                            value={form.severity}
                            onChange={e => setForm(f => ({...f, severity: e.target.value}))}
                        >
                            <option value="">Все</option>
                            {LOG_SEVERITIES.map(s => (
                                <option key={s} value={s}>
                                    {s}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
                <div className="flex gap-2 sm:justify-end md:col-span-2 md:pb-[1px]">
                    <button
                        type="button"
                        className="rounded-md border border-[#d8dce6] bg-[#fbfcff] px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-[#c2c9d8] hover:bg-white hover:shadow-sm sm:text-sm"
                        onClick={reset}
                    >
                        Сбросить
                    </button>
                    <button
                        type="button"
                        className="rounded-md border px-3.5 py-1.5 text-xs font-semibold text-white shadow-[0_4px_12px_rgba(159,45,32,0.25)] transition hover:-translate-y-[1px] hover:brightness-110 sm:text-sm"
                        style={{background: "linear-gradient(135deg, #9F2D20 0%, #7f2419 100%)", borderColor: "#7f2419"}}
                        onClick={apply}
                    >
                        Применить
                    </button>
                </div>
            </div>
            <div className="min-h-[14px]">{error ? <p className="text-xs text-red-600 sm:text-sm">{error}</p> : null}</div>
        </div>
    )
}
