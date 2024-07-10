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
    // {
    // cycode_secret_ignore_here	
    //   name: 'Jean Michel'
    // cycode_secret_ignore_here		
    //   user_email: 'jean.michel@filigran.test',
    // cycode_secret_ignore_here		
    //   password: 'jeanmichel',
    //   groups: ['Dashboards group'],
    // },
  ]);
});
