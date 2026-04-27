import type { ConsolePayload } from '../types/console'

import { ArtifactsNewPage } from './ArtifactsNewPage'

type ArtifactsPageProps = {
  data: ConsolePayload | null
}

function ArtifactsPage({ data }: ArtifactsPageProps) {
  return <ArtifactsNewPage data={data} />
}

export default ArtifactsPage
