import React, { useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Calendar, User, LogOut, Plus, Ticket, Shield } from 'lucide-react';

const Navbar = () => {
  const { user, login, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  return (
    <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/events" className="flex items-center space-x-2">
            <Calendar className="w-8 h-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">EventHub</span>
          </Link>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Button
                  data-testid="create-event-nav-btn"
                  onClick={() => navigate('/create-event')}
                  className="hidden sm:flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-full"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create Event</span>
                </Button>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button data-testid="user-menu-btn" className="flex items-center space-x-2 focus:outline-none">
                      <Avatar className="w-9 h-9 border-2 border-blue-600">
                        <AvatarImage src={user.picture} alt={user.name} />
                        <AvatarFallback>{user.name?.charAt(0)}</AvatarFallback>
                      </Avatar>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="px-2 py-2">
                      <p className="text-sm font-semibold">{user.name}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem data-testid="my-events-menu-item" onClick={() => navigate('/my-events')} className="cursor-pointer">
                      <Calendar className="w-4 h-4 mr-2" />
                      My Events
                    </DropdownMenuItem>
                    <DropdownMenuItem data-testid="my-bookings-menu-item" onClick={() => navigate('/my-bookings')} className="cursor-pointer">
                      <Ticket className="w-4 h-4 mr-2" />
                      My Bookings
                    </DropdownMenuItem>
                    <DropdownMenuItem className="sm:hidden cursor-pointer" onClick={() => navigate('/create-event')}>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Event
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem data-testid="logout-btn" onClick={logout} className="cursor-pointer text-red-600">
                      <LogOut className="w-4 h-4 mr-2" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <Button
                data-testid="login-btn"
                onClick={login}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-full flex items-center space-x-2"
              >
                <User className="w-4 h-4" />
                <span>Sign In</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
