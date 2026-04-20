import { type JSX, useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { checkBackend } from "../api/fetchLogs"
import { checkAuth, logout } from "./TokenCheck"
import { ApiError, ApiErrorCode, handleApiError } from "./notify"

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
    const [state, setState] = useState<"loading" | "ok" | "fail">("loading")

    useEffect(() => {
        const run = async () => {
            try {
                // 1. проверка backend
                await checkBackend()

                // 2. проверка auth
                await checkAuth()

                setState("ok")
            } catch (e) {
                handleApiError(e)

                // 3. logout ТОЛЬКО для auth проблем
                if (
                    e instanceof ApiError &&
                    (e.code === ApiErrorCode.NO_TOKEN ||
                        e.code === ApiErrorCode.UNAUTHORIZED)
                ) {
                    await logout()
                }

                setState("fail")
            }
        }

        run()
    }, [])

    if (state === "loading") {
        return <div>Loading...</div>
    }

    if (state === "fail") {
        return <Navigate to="/login" replace />
    }

    return children
}