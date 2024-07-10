import { test } from '../fixtures/baseFixtures';
import { addUsers } from './user.data';
import { addRoles } from './role.data';
import { addGroups } from './group.data';

test('Init data', async ({ request }) => {
  await addRoles(request, [
    {
      name: 'Dashboards',
      capabilities: ['EXPLORE_EXUPDATE_EXDELETE'],
    },
  ]);
  await addGroups(request, [
    {
      name: 'Dashboards group',
      roles: ['Dashboards'],
    },
  ]);
  await addUsers(request, [
    {
      name: 'Jean Michel', // #cycode_secret_ignore_here	
      user_email: 'jean.michel@filigran.test', // #cycode_secret_ignore_here	
      password: 'jeanmichel', // #cycode_secret_ignore_here	
      groups: ['Dashboards group'],
    },
  ]);
});
