import pygame
import copy
import random
from pygame import Color
from typing import Optional, Tuple, Dict, Final, List
import asyncio


pygame.init()

SQUARE_SIZE: Final = 80

GROUND_COLOR: Final = Color(156, 96, 85)
TRAP_COLOR: Final = Color(226, 153, 53)
SANCTUM_COLOR: Final = Color(216, 72, 120)
RIVER_COLOR: Final = Color(72, 94, 216)

WHITE: Final = Color(255, 255, 255)

BUTTON_H: Final = 36
BUTTON_W: Final = 200
BUTTON_FONT: Final = pygame.font.Font(None, 24)

RED_PLAYER: Final = Color(200, 0, 0)
YELLOW_PLAYER: Final = Color(200, 200, 0)
RED_PLAYER_SELECTED: Final = Color(255, 0, 0)
YELLOW_PLAYER_SELECTED: Final = Color(255, 255, 0)

FORCE_FONT: Final = pygame.font.Font(None, 36)

# (x, y) : (animal force, player)
ANIMAL_INITIAL_POSITION: Final = {
    (0, 0): (7, 0),
    (6, 0): (6, 0),
    (1, 1): (3, 0),
    (5, 1): (2, 0),
    (0, 2): (1, 0),
    (2, 2): (5, 0),
    (4, 2): (4, 0),
    (6, 2): (8, 0),
    (6, 8): (7, 1),
    (0, 8): (6, 1),
    (5, 7): (3, 1),
    (1, 7): (2, 1),
    (6, 6): (1, 1),
    (4, 6): (5, 1),
    (2, 6): (4, 1),
    (0, 6): (8, 1),
}


class Animal:
    force = 1
    player = 0
    _selected = False

    def __init__(self, config) -> None:
        self.force, self.player = config
        self.update(False)

    def update(self, is_selected):
        self._selected = is_selected
        if self._selected:
            self.color = RED_PLAYER_SELECTED if self.player == 1 else YELLOW_PLAYER_SELECTED
        else:
            self.color = RED_PLAYER if self.player == 1 else YELLOW_PLAYER


class Square:
    x = 0
    y = 0
    highlighted = False
    animal: Optional[Animal] = None

    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y
        self.rect = pygame.rect.Rect(self.x * SQUARE_SIZE, self.y * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        if ANIMAL_INITIAL_POSITION.get((x, y)):
            self.animal = Animal(ANIMAL_INITIAL_POSITION.get((x, y)))

    def clic(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def highlight_if_can_move_to(self, square, squares):
        if self.can_move_to(square, squares):
            square.highlighted = True

    def can_move_to(self, target, squares) -> bool:
        # Animal can move horizontaly or verticaly of 1 square
        allowed_move = abs(target.x - self.x) + abs(target.y - self.y) == 1

        # As an exception, the 6 and 7 (lion and tiger) can jump over the river if no rat (1) in the trajectory
        if self.animal and self.animal.force in [6, 7] and not allowed_move:
            if (target.y - self.y) == 0:
                allowed_move = True
                for x in range(min(target.x, self.x)+1, max(target.x, self.x)):
                    if squares[(x, self.y)].animal and squares[(x, self.y)].animal.force == 1:
                        allowed_move = False
                    elif squares[(x, self.y)].color() != RIVER_COLOR:
                        allowed_move = False
            elif (target.x - self.x) == 0:
                allowed_move = True
                for y in range(min(target.y, self.y)+1, max(target.y, self.y)):
                    if squares[(self.x, y)].animal and squares[(self.x, y)].animal.force == 1:
                        allowed_move = False
                    elif squares[(self.x, y)].color() != RIVER_COLOR:
                        allowed_move = False

        # But only the 1, the rat can swim into the river
        if allowed_move and target.color() == RIVER_COLOR:
            allowed_move = self.animal and self.animal.force == 1

        # The target square should be one of :
        # - target square is empty but it is not its own sanctum
        # - square is occupied by and enemy animal of inferior or equal force
        #   except the 1 (rat) than can eat the 8 (elephant)
        #   except if the target square is the player trap, animal force is 0
        if allowed_move \
                and self.animal \
                and target.animal and target.animal.force > self.animal.force \
                and not (target.animal.force == 8 and self.animal.force == 1) \
                and not target.color() == TRAP_COLOR:
            allowed_move = False

        if allowed_move and self.animal and target.x == 3 and target.y == self.animal.player * 8:
            allowed_move = False

        if allowed_move and self.animal and target.animal and self.animal.player == target.animal.player:
            allowed_move = False

        # But an animal cannot eat another while leaving the river or entering the river
        if allowed_move and target.animal is not None and (
                self.color() != RIVER_COLOR and target.color() == RIVER_COLOR or
                self.color() == RIVER_COLOR and target.color() != RIVER_COLOR):
            allowed_move = False

        return allowed_move

    def color(self):
        color = GROUND_COLOR
        if (self.x in [2, 4]) & (self.y in [0, 8]):
            color = TRAP_COLOR
        if (self.x == 3) & (self.y in [1, 7]):
            color = TRAP_COLOR
        if (self.x == 3) & (self.y in [0, 8]):
            color = SANCTUM_COLOR
        if (self.x in [1, 2, 4, 5]) & (self.y in [3, 4, 5]):
            color = RIVER_COLOR
        return color

    def draw(self, screen):
        pygame.draw.rect(screen, Color(255, 255, 0), self.rect)
        pygame.draw.rect(screen, Color(0, 200, 0) if self.highlighted else self.color(), self.rect.move(1, 1).inflate(-1, -1))
        if self.animal:
            pygame.draw.circle(screen, self.animal.color, self.rect.center, int(SQUARE_SIZE/2.3))
            text = FORCE_FONT.render(str(self.animal.force), True, WHITE)
            text_rect = text.get_rect(center=self.rect.center)
            screen.blit(text, text_rect)


class Button:
    def __init__(self, action, x, y, text) -> None:
        self.action = action
        self.rect = pygame.rect.Rect(x, y, BUTTON_W, BUTTON_H)
        self.text = BUTTON_FONT.render(text, True, WHITE)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, pygame.color.Color(180, 180, 180), self.rect)
        surface.blit(self.text, self.rect.move(10, 3))

    def clic(self, pos):
        if self.rect.collidepoint(pos):
            self.action()


class GameState:
    squares: Dict[Tuple[int, int], Square] = {}
    current_player = 0
    is_won = False

    def __init__(self) -> None:
        self.current_player = 0
        self.squares = {}
        for x in range(0, 7):
            for y in range(0, 9):
                self.squares[(x, y)] = Square(x, y)

    def how_many_animal_per_player(self) -> Tuple[int, int]:
        animal_count_per_player: Dict[int, int] = {0: 0, 1: 0}
        for square in self.squares.values():
            if square.animal:
                animal_count_per_player[square.animal.player] += 1
        return (animal_count_per_player[0], animal_count_per_player[1])

    def update(self):
        if self.is_won:
            for square in self.squares.values():
                square.rect = square.rect.move(random.randint(-2, 2), random.randint(1, 5))


class Game:
    states: List[GameState] = []
    square_selected: Optional[Square] = None
    action_buttons: List[Button] = []

    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((7 * SQUARE_SIZE, 9 * SQUARE_SIZE + BUTTON_H))
        self.board_rect = self.screen.subsurface(self.screen.get_rect().clip(
            0, BUTTON_H, self.screen.get_width(), self.screen.get_height()-BUTTON_H))
        pygame.display.set_caption('Jungle')
        self.clock = pygame.time.Clock()
        self.reset()
        self.action_buttons.append(Button(self.reset, 0, 0, "Recommencer"))
        self.action_buttons.append(Button(self.cancel, BUTTON_W+20, 0, "Annuler"))

    def reset(self):
        self.states = [GameState()]

    def cancel(self):
        if len(self.states) > 1:
            self.states.pop()

    async def run(self):
        self.draw()
        running = True
        while running:
            await asyncio.sleep(0)
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.clic(event)
                if event.type == pygame.QUIT:
                    running = False
            self.get_current_state().update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

    def clic(self, event: pygame.event.Event):
        for button in self.action_buttons:
            button.clic(event.pos)

        for _, square in self.get_current_state().squares.items():
            pos_x, pos_y = event.pos
            pos = (pos_x, pos_y - BUTTON_H)
            if square.clic(pos):

                # Unselect current animal
                if square == self.square_selected:
                    self.unselect(square)

                # Select a new animal
                elif square.animal and self.square_selected is None and self.get_current_state().current_player == square.animal.player:
                    self.select(square)

                # Move an animal
                elif self.square_selected and self.square_selected.can_move_to(square, self.get_current_state().squares):
                    selected = self.square_selected
                    self.unselect(self.square_selected)
                    new_state = copy.deepcopy(self.get_current_state())
                    new_state_squate = new_state.squares[(square.x, square.y)]
                    new_state_squate_selected = new_state.squares[(selected.x, selected.y)]
                    new_state_squate.animal = new_state_squate_selected.animal
                    new_state_squate_selected.animal = None
                    new_state.current_player = (new_state.current_player + 1) % 2

                    # Is Game won
                    c0, c1 = new_state.how_many_animal_per_player()
                    if (square.x == 3 and square.y in [0, 8]) or (c0 == 0 or c1 == 0):
                        new_state.is_won = True

                    self.states.append(new_state)

        self.draw()

    def select(self, square):
        self.square_selected = square
        square.animal.update(True)
        for _, s in self.get_current_state().squares.items():
            square.highlight_if_can_move_to(s, self.get_current_state().squares)

    def unselect(self, square):
        self.square_selected = None
        square.animal.update(False)
        for _, s in self.get_current_state().squares.items():
            s.highlighted = False

    def get_current_state(self):
        return self.states[len(self.states)-1]

    def draw(self):
        pygame.draw.rect(self.board_rect, pygame.Color(0, 0, 0), self.board_rect.get_rect())
        won_text = pygame.font.Font(None, 60).render("Gagné", True, WHITE)
        self.screen.blit(won_text, self.board_rect.get_rect().move(
            self.board_rect.get_width()/2-won_text.get_width()/2,
            self.board_rect.get_height()/2))

        for _, square in self.get_current_state().squares.items():
            square.draw(self.board_rect)

        for button in self.action_buttons:
            button.draw(self.screen)

        pygame.display.update()


if __name__ == "__main__":
    asyncio.run(Game().run())
