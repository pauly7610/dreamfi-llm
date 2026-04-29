import type { ConsolePayload } from '../types/console'

import { ArtifactsNewPage } from './ArtifactsNewPage'

type ArtifactsPageProps = {
  data: ConsolePayload | null
  onDataChanged?: () => void
}

function ArtifactsPage({ data, onDataChanged }: ArtifactsPageProps) {
  return <ArtifactsNewPage data={data} onDataChanged={onDataChanged} />
}

export default ArtifactsPage
