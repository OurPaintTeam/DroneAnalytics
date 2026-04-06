import {useId, useState, type CSSProperties} from "react"

import {RED} from "../config"
import {LOG_SERVICE_TYPES, LOG_SEVERITIES} from "../logConstants"
import {buildEventSafetySearchParams, type EventSafetyFilterForm} from "../logQuery"
import MUIRangePicker from "./DateRangePicker"

type Props = {
    onApply: (params: URLSearchParams) => void
}

const fieldClass =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-0"

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
        <div className="rounded-xl border border-gray-200 bg-white p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-2">
                <h3 className="text-sm font-medium tracking-tight text-gray-800">Фильтры</h3>
            </div>

            <div className="grid gap-5 lg:grid-cols-12 lg:items-end lg:gap-x-6 lg:gap-y-4">
                <div className="lg:col-span-5">
                    <label className="mb-1.5 block text-xs font-medium text-gray-500">
                        Период <span className="font-normal text-gray-400">· timestamp записей, мс UTC</span>
                    </label>
                    <MUIRangePicker
                        variant="inline"
                        from={form.from}
                        to={form.to}
                        onChange={(from, to) => setForm(f => ({...f, from, to}))}
                    />
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:col-span-7">
                    <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium text-gray-500">Сервис</span>
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
                    <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium text-gray-500">ID сервиса</span>
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
                    <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium text-gray-500">Важность</span>
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
            </div>

            <div className="mt-5 flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                    {error ? <p className="text-sm text-red-600">{error}</p> : null}
                </div>
                <div className="flex shrink-0 flex-wrap justify-end gap-2">
                    <button
                        type="button"
                        className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 transition hover:bg-gray-50"
                        onClick={reset}
                    >
                        Сбросить
                    </button>
                    <button
                        type="button"
                        className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                        onClick={apply}
                    >
                        Применить
                    </button>
                </div>
            </div>
        </div>
    )
}
