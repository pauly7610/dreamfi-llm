import type { ConsolePayload } from '../types/console'

import { TrustNewPage } from './TrustNewPage'

type TrustPageProps = {
  data: ConsolePayload | null
}

function TrustPage({ data }: TrustPageProps) {
  return <TrustNewPage data={data} />
}

export default TrustPage
