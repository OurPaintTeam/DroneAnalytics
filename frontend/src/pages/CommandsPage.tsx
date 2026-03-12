import {useEffect} from "react"
import {useNavigate} from "react-router-dom"
import {checkAuth} from "../components/TokenCheck.ts"

const CommandsPage = () => {
    const navigate = useNavigate()

    useEffect(() => {

        const init = async () => {

            const authorized = await checkAuth()

            if (!authorized) {
                navigate("/login")
                return
            }
        }
        init()
    }, [navigate])

    return (
        <div className="min-h-screen flex items-center justify-center">
            <h1 className="text-3xl font-bold text-gray-700">
                Commands Page
            </h1>
        </div>
    )
}

export default CommandsPage