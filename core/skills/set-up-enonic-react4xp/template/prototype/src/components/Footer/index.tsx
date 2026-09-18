// libraries
import { useEffect, useRef, useState } from 'react'
import dayjs from 'dayjs'

// types
interface FooterProps {
    
}

// css
import './index.scss'

export default function Footer({
    
}: FooterProps) {
    const [footerDate, setFooterDate] = useState<string | null>(null)

    useEffect(() => {
        setFooterDate(dayjs().format('DD.MM.YYYY HH:mm:ss:SSS'))
    }, [])

    return (
        <footer className='footer-component'>
            <div>TODO: Footer ({footerDate})</div>
        </footer>
    )
}