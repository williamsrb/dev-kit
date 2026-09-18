export default function Home() {
	return (
		<main className='prototype'>
			<div className='container'>

				<h1 className='h2' >
					Front-end pages and components for {PROJECT_SHORT_NAME}
				</h1>

				<p className='body' style={{
					marginTop: '2rem',
					marginBottom: '4rem'
				}}>
					- Press shift+g to toggle the grid<br />
					- <a
						href='#'
						target='_blank'
						rel='noopener noreferrer'
						className='simple-link'
					>
						Figma link
					</a>
				</p>

				{[
					{
						title: 'Assets',
						items: []
					},
					{
						title: 'Components',
						items: []
					},
					{
						title: 'Pages',
						items: []
					}
				].map((item, i) => (
					<div key={i} className='prototype__section'>

						<h2 className='h4'>
							{item.title}
						</h2>

						<div className='prototype__links'>
							{item.items.map((subItem: any, i2: number) => (
								<div key={i2}>
									<a
										href={subItem.href}
										className='button-black'
									>
										{subItem.label}
									</a>
								</div>
							))}
						</div>

					</div>
				))}

			</div>
		</main>
	)
}