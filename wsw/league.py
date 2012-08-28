from flask import g 
from datetime import timedelta


class Season:

    id = None
    signup_limit = 0
    signups_open = False


    def __init__(self, id):
        self.id = id


    def get_matches(self):
        from wsw import query_db
        query = """
        SELECT matches.id, auser.id, auser.username, buser.id, buser.username,
        scheduled FROM matches
        LEFT JOIN match_players AS alpha 
        ON alpha.match_id = matches.id AND alpha.alpha = 1
        LEFT JOIN users AS auser ON auser.id = alpha.user_id
        LEFT JOIN match_players AS beta 
        ON beta.match_id = matches.id AND beta.alpha = 0
        LEFT JOIN users AS buser ON buser.id = beta.user_id
        WHERE season_id = ?
        """
        values = (self.id)
        cur = g.db.execute(query, values)
        results = []
        for row in cur.fetchall():
            match = {
                    'id' : row[0],
                    'scheduled' : row[5],
                    'alpha' : {
                        'id' : row[1],
                        'username' : row[2]
                        },
                    'beta' : {
                        'id' : row[3],
                        'username' : row[4]
                        }
                    }
            results = results + [match]

        return results


    def create_matches(self, division_number, maps, start, interval):
        query = """
        SELECT user_id FROM signups
        WHERE season_id = ?
        AND division = ?
        """
        values = (self.id, division_number)

        cur = g.db.execute(query, values)

        def get_id(arg):
            return arg[0]

        teams = map(get_id, cur.fetchall())

        if len(teams) % 2 == 1: teams = teams + [None]
        s = []

        for i in range(len(teams)-1):

            mid = len(teams) / 2
            l1 = teams[:mid]
            l2 = teams[mid:]
            l2.reverse()    

            # Switch sides after each round
            if(i % 2 == 1):
                s = s + [zip(l1, l2)]
            else:
                s = s + [zip(l2, l1)]
            teams.insert(1, teams.pop())

        if (interval == "w"):
            td = timedelta(weeks=1)
        elif (interval == "d"):
            td = timedelta(days=1)

        for round in range(len(s)):
            for match in s[round]:
                # Match
                query = """
                INSERT INTO matches(season_id, scheduled, round)
                VALUES(?, ?, ?)
                """

                scheduled = start + (round * td)
                values = (self.id, scheduled, round)
                cur = g.db.execute(query, values)
                if not cur.rowcount:
                    # TODO log
                    g.db.rollback()
                    return False

                # Players
                match_id = cur.lastrowid
                query = """
                INSERT INTO match_players(match_id, user_id, alpha)
                VALUES(?, ?, ?)
                """
                values = ((match_id, match[0], True), (match_id, match[1], False))
                cur = g.db.executemany(query, values)
                if cur.rowcount != 2:
                    g.db.rollback()
                    return False

                # Maps
                values = []
                for i in range(maps):
                    values = values + [ (match_id, i) ]
                query = """
                INSERT INTO results(match_id, game_id)
                VALUES(?, ?)
                """
                cur = g.db.executemany(query, values)
                if cur.rowcount != maps:
                    g.db.rollback()
                    return False

        g.db.commit()
        return True


    def remove_signups(self, users):
        query = """
        DELETE FROM signups 
        WHERE season_id = ?
        AND user_id IN (?)
        """

        for user_id in users:
            values = (self.id, user_id)
            cur = g.db.execute(query, values)
            if not cur.rowcount:
                g.db.rollback()
                return False

        g.db.commit()
        return True


    def add_to_division(self, division, users):
        if division <= 0:
            return False

        query = """
        UPDATE signups SET division = ?
        WHERE season_id = ? 
        AND user_id = ?
        """
        for user_id in users:
            values = (division, self.id, user_id)
            cur = g.db.execute(query, values)
            if not cur.rowcount:
                g.db.rollback()
                return False

        g.db.commit()
        return True


    def remove_from_division(self, user_id):
        query = """
        UPDATE signups SET division = NULL
        WHERE season_id = ?
        AND user_id = ?
        """
        values = (self.id, user_id)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            g.db.commit()
            return True

        g.db.rollback()
        return False


    @staticmethod
    def remove_signup(season_id, user_id):
        query = """
        DELETE FROM signups
        WHERE season_id = ?
        AND user_id = ?
        """
        values = (season_id, user_id)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            g.db.commit()
            return True

        g.db.rollback()
        return False


    def get_unasigned_signup_list(self):
        query = """
        SELECT user_id, username FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ? AND signups.division IS NULL
        """
        cur = g.db.execute(query, (self.id))
        return cur.fetchall()


    def get_signups(self):
        from wsw import query_db
        query = """
        SELECT users.id, username, division FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ?
        """
        return query_db(query, (self.id))


    def get_waiting_list(self):
        from wsw import query_db
        query = """
        SELECT users.id, users.username, signups.division
        FROM signups
        LEFT JOIN users ON users.id = signups.user_id
        WHERE signups.season_id = ? AND signups.division IS NULL
        """
        return query_db(query, (self.id))

    def get_map_pool(self):
        from wsw import query_db
        query = """
        SELECT id, name FROM season_maps
        LEFT JOIN maps ON maps.id = map_id
        WHERE season_id = ?
        """
        return query_db(query, (self.id))

    def get_maps_not_in_pool(self):
        query = """
        SELECT id, name FROM maps
        WHERE id NOT IN
        (SELECT map_id FROM season_maps WHERE season_id = ?)
        """
        cur = g.db.execute(query, (self.id))
        return cur.fetchall()

    def get_users_for_signup(self):
        query = """
        SELECT id, username FROM users
        WHERE id NOT IN
        (SELECT user_id FROM signups WHERE season_id = ?)
        """
        return g.db.execute(query, (self.id))

    
    def get_division_numbers(self):
        from wsw import query_db
        query = """
        SELECT MAX(division) as max FROM signups
        WHERE season_id = ? ORDER BY division ASC
        """
        max = query_db(query, (self.id), True)['max']
        if max:
            return range(1, max+1)
        return None


    def get_divisions(self):
        divisions_numbers = self.get_division_numbers()
        if divisions_numbers:
            divisions = []
            for i in divisions_numbers:
                divisions = divisions + [self.get_division(i)]
            return divisions

        return None


    def get_division(self, division):
        from wsw import query_db
        query = """
        SELECT users.id, username, division FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ?
        AND division = ?
        """
        values = (self.id, division)
        return query_db(query, values)


    def load(self, id=None):
        from wsw import query_db
        if not id:
            if not self.id:
                return
            id = self.id
        query = 'SELECT * FROM seasons WHERE id = ?'
        data = query_db(query, (id), True)
        self.signup_limit = data['signup_limit']
        self.signups_open = data['signups_open']


    @staticmethod
    def get_current_season_id():
        query = 'SELECT id FROM seasons ORDER BY id DESC LIMIT 1'
        cur = g.db.execute(query)
        season = cur.fetchone()
        if season:
            return season[0]
        return None


    @staticmethod
    def get_seasons_list():
        from wsw import query_db
        query = 'SELECT id FROM seasons'
        return query_db(query)


