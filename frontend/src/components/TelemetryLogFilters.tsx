import {useId, useState, type CSSProperties} from "react"

import {RED} from "../config"
import {LOG_DRONE_TYPES} from "../logConstants"
import {buildTelemetrySearchParams, type TelemetryFilterForm} from "../logQuery"
import MUIRangePicker from "./DateRangePicker"

type Props = {
    onApply: (params: URLSearchParams) => void
}

const fieldClass =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-offset-0"

const emptyForm = (): TelemetryFilterForm => ({
    from: null,
    to: null,
    drone: "",
    droneIdRaw: "",
})

export default function TelemetryLogFilters({onApply}: Props) {
    const baseId = useId()
    const [form, setForm] = useState<TelemetryFilterForm>(emptyForm)
    const [error, setError] = useState<string | null>(null)

    const apply = () => {
        const {params, error: err} = buildTelemetrySearchParams(form)
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
                        Период <span className="font-normal text-gray-400">· мс UTC</span>
                    </label>
                    <MUIRangePicker
                        variant="inline"
                        from={form.from}
                        to={form.to}
                        onChange={(from, to) => setForm(f => ({...f, from, to}))}
                    />
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:col-span-7">
                    <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium text-gray-500">Тип дрона</span>
                        <select
                            id={`${baseId}-drone`}
                            className={fieldClass}
                            style={ringFocus}
                            value={form.drone}
                            onChange={e => setForm(f => ({...f, drone: e.target.value}))}
                        >
                            <option value="">Все</option>
                            {LOG_DRONE_TYPES.map(d => (
                                <option key={d} value={d}>
                                    {d}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="flex flex-col gap-1.5">
                        <span className="text-xs font-medium text-gray-500">ID дрона</span>
                        <input
                            id={`${baseId}-did`}
                            type="text"
                            inputMode="numeric"
                            autoComplete="off"
                            placeholder="≥ 1"
                            className={fieldClass}
                            style={ringFocus}
                            value={form.droneIdRaw}
                            onChange={e => setForm(f => ({...f, droneIdRaw: e.target.value}))}
                        />
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
