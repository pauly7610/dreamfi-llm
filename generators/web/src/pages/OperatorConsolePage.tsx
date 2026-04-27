import type { ConsolePayload } from '../types/console'

import { HomeNewPage } from './HomeNewPage'

type OperatorConsolePageProps = {
  data: ConsolePayload | null
  error: string | null
  loading: boolean
  retry: () => void
}

function OperatorConsolePage({ data, error, retry }: OperatorConsolePageProps) {
  return <HomeNewPage data={data} error={error} retry={retry} />
}

export default OperatorConsolePage
