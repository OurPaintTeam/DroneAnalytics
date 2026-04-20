import {type JSX, useEffect, useState} from "react"
import { Navigate } from "react-router-dom"
import { checkAuth } from "./TokenCheck"
import { logout } from "./TokenCheck"

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
    const [isAuth, setIsAuth] = useState<boolean | null>(null)

    useEffect(() => {
        checkAuth().then(setIsAuth)
    }, [])

    useEffect(() => {
        if (isAuth === false) {
            logout()
        }
    }, [isAuth])

    if (isAuth === null) {
        return <div>Loading...</div>
    }

    if (!isAuth) {
        return <Navigate to="/login" replace />
    }

    return children
}