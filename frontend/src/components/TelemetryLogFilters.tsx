import {useId, useState, type CSSProperties} from "react"


import {RED} from "../config"

import {LOG_DRONE_TYPES} from "../logConstants"

import {buildTelemetrySearchParams, type TelemetryFilterForm} from "../logQuery"

import MUIRangePicker from "./DateRangePicker"


type Props = {

    onApply: (params: URLSearchParams) => void

}


const fieldClass =

    "w-full rounded-md border border-[#d8dce6] bg-[#fbfcff] px-2.5 py-1.5 text-sm text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] transition placeholder:text-slate-400 hover:border-[#bfc5d5] hover:shadow-[0_0_0_3px_rgba(159,45,32,0.06)] focus:border-[#9F2D20] focus:bg-white focus:outline-none focus:ring-2 focus:ring-offset-0"


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

        <div className="space-y-3">

            <div className="grid gap-2.5 md:grid-cols-12 md:items-end md:gap-x-3">

                <div className="md:col-span-4">

                    <label className="mb-1 block text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">

                        Период

                    </label>

                    <MUIRangePicker

                        variant="inline"

                        from={form.from}

                        to={form.to}

                        onChange={(from, to) => setForm(f => ({...f, from, to}))}

                    />

                </div>


                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:col-span-6">

                    <label className="flex flex-col gap-1">

                            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">

                                Тип дрона

                            </span>

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

                    <label className="flex flex-col gap-1">

                            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">

                                ID дрона

                            </span>

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

                <div className="flex gap-2 sm:justify-end md:col-span-2 md:pb-[1px]">

                    <button

                        type="button"

                        className="rounded-md border border-[#d8dce6] bg-white/90 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:border-[#c2c9d8] hover:bg-white hover:shadow sm:text-sm"

                        onClick={reset}

                    >

                        Сбросить

                    </button>

                    <button

                        type="button"

                        className="rounded-md border px-3.5 py-1.5 text-xs font-semibold text-white shadow-[0_4px_14px_rgba(159,45,32,0.28)] transition hover:-translate-y-px hover:brightness-110 active:translate-y-0 sm:text-sm"

                        style={{
                            background: "linear-gradient(135deg, #9F2D20 0%, #7f2419 100%)",
                            borderColor: "#7f2419"
                        }}

                        onClick={apply}

                    >

                        Применить

                    </button>

                </div>

            </div>

            <div className="min-h-[14px] px-0.5">

                {error ? <p className="text-xs text-red-600 sm:text-sm">{error}</p> : null}

            </div>

        </div>

    )

}

