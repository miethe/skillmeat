import { permanentRedirect } from 'next/navigation';

/**
 * Deployment Set Detail Page — deprecated
 *
 * The detail view has moved to a modal on the deployment sets list page.
 * Permanently redirect all direct URL visits back to the list page.
 */
export default function DeploymentSetDetailPage() {
  permanentRedirect('/deployment-sets');
}
