// libraries
import type { Metadata } from 'next'

// metadata
export const metadata: Metadata = {
	title: '{PROJECT_SHORT_NAME}',
	description: '{PROJECT_DISPLAY_NAME}',
	icons: {
		icon: '/img/favicon.png',
	}
}

// css

// components
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import Guidelines from '@/components/Guidelines'

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode
}>) {
	return (
		<html lang='no'>
			<body id='start'>

				<div id='portal' />

				<Header />

				<div id='main-content'>
					{children}
				</div>
				
				<Footer />

				<Guidelines />

			</body>
		</html>
	);
}
