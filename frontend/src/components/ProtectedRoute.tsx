import { type JSX, useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { checkBackend } from "../api/fetchLogs"
import { checkAuth, logout } from "./TokenCheck"
import { ApiError, ApiErrorCode, handleApiError } from "./notify"
import ErrorPage from "../pages/ErrorPage.tsx";

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
    const [state, setState] =
        useState<"loading" | "ok" | "auth_fail" | "backend_down">("loading")

    useEffect(() => {
        const run = async () => {
            try {
                await checkBackend()
                await checkAuth()
                setState("ok")
            } catch (e) {

                handleApiError(e)

                if (e instanceof ApiError) {

                    if (e.code === ApiErrorCode.BACKEND_DOWN) {
                        setState("backend_down")
                        return
                    }

                    if (
                        e.code === ApiErrorCode.NO_TOKEN ||
                        e.code === ApiErrorCode.UNAUTHORIZED
                    ) {
                        await logout()
                        setState("auth_fail")
                        return
                    }
                }

                setState("backend_down")
            }
        }

        run()
    }, [])

    if (state === "backend_down") {
        return <ErrorPage
            customTitle="Сервер недоступен"
            customMessage="Сервер временно недоступен. Пожалуйста, попробуйте позже."
        />
    }

    if (state === "loading") {
        return <div>Loading...</div>
    }

    if (state === "auth_fail") {
        return <Navigate to="/login" replace />
    }

    return children
}